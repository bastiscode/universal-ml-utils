from typing import Generator

try:
    import torch
    from torch.nn.utils.rnn import pad_sequence
except ImportError:
    raise ImportError("torch needs to be installed to use the decoding module.")


from universal_ml_utils.decoding.utils import (
    Beam,
    CacheFn,
    DecodeFn,
    LogitFn,
    SampleFn,
    ScoreFn,
    StopFn,
    UpdateFn,
    greedy,
    identity_update,
    log_likelihood_score,
)


@torch.inference_mode()
def beam_search(
    decode_fn: DecodeFn,
    initial: list[list[int]] | list[Beam],
    pad_token_id: int,
    max_length: int,
    stop_fn: StopFn,
    device: torch.device,
    beam_width: int,
    sample_fn: SampleFn = greedy(),
    update_fn: UpdateFn = identity_update(),
    score_fn: ScoreFn = log_likelihood_score(),
    logit_fns: list[LogitFn] | None = None,
    cache_fn: CacheFn | None = None,
    stop_condition: str = "estimated_score",
    max_new_tokens: int | None = None,
    yield_intermediate: bool = False,
    return_unfinished: bool = False,
) -> Generator[list[list[Beam]], None, list[list[Beam]]]:
    assert max_new_tokens is None or max_new_tokens > 0, (
        "max_new_tokens must be None or positive"
    )
    assert stop_condition in {
        "max_score",
        "estimated_score",
        "max_outputs",
    }, "stop condition must be 'max_score', 'estimated_score' or 'max_outputs'"
    assert beam_width >= 1, "beam width must be greater than or equal to 1"
    batch_size = len(initial)

    current_beams: list[list[Beam]] = []
    finished_beams: list[list[Beam]] = []
    too_long_beams: list[list[Beam]] = []

    for init in initial:
        assert len(init) > 0, "initial beam or token ids cannot be empty"
        if isinstance(init, Beam):
            beams = [init]
        else:
            # init beam from token ids
            beams = [Beam(init)]

        current_beams.append(beams)  # type: ignore
        finished_beams.append([])
        too_long_beams.append([])

    def too_long(beam: Beam) -> bool:
        if len(beam) >= max_length:
            return True
        elif max_new_tokens is None:
            return False
        else:
            return beam.decoded_length >= max_new_tokens

    def filter_beams() -> tuple[list[Beam], list[int]]:
        for idx in range(batch_size):
            new_beams = []
            for beam in current_beams[idx]:
                if stop_fn(beam):
                    beam.stop_reason = "done"
                    finished_beams[idx].append(beam)
                elif too_long(beam):
                    beam.stop_reason = "length"
                    too_long_beams[idx].append(beam)
                else:
                    new_beams.append(beam)

            current_beams[idx] = new_beams
            if not new_beams:
                # we are done with this batch element
                continue

            elif len(finished_beams[idx]) < beam_width:
                continue

            elif stop_condition == "max_outputs":
                # we are done with this batch element
                # because we have enough finished beams
                current_beams[idx] = []
                continue

            worst_finished = min(
                (score_fn(b) for b in finished_beams[idx]),
                default=float("-inf"),
            )
            if stop_condition == "estimated_score":
                # best current calculated from current length
                # idea: is a current active beam better than the worst finished beam?
                best_current = max(score_fn(b) for b in current_beams[idx])
            else:
                # best current calculated from maximum length
                # idea: assume all remaining tokens are perfectly predicted
                # with probability 1.0, can a current active beam be better
                # than the worst finished beam?
                current = next(b for b in current_beams[idx])
                max_decoded_length = max_length - current.initial_length
                length = min(max_decoded_length, max_new_tokens or max_decoded_length)
                best_current = max(score_fn(b, length) for b in current_beams[idx] if b)

            if worst_finished >= best_current:
                # set current beams to None list to stop processing
                current_beams[idx] = []

        beams = []
        indices = []
        for idx in range(batch_size):
            beams.extend(current_beams[idx])
            indices.extend([idx] * len(current_beams[idx]))
        return beams, indices

    def get_outputs() -> list[list[Beam]]:
        outputs = []
        for batch_idx in range(batch_size):
            finished = finished_beams[batch_idx]

            if return_unfinished and len(finished) < beam_width:
                too_long = sorted(too_long_beams[batch_idx], key=score_fn, reverse=True)
                finished.extend(too_long[: beam_width - len(finished)])

            finished = sorted(finished, key=score_fn, reverse=True)
            outputs.append(finished[:beam_width])

        return outputs

    single = beam_width == 1
    beams, indices = filter_beams()
    cache = None

    while beams:
        if cache is not None and all(beam.cache is not None for beam in beams):
            assert cache_fn is not None, "cache_fn must be provided if cache is used"
            cache_mask = [beam.cache for beam in beams]
            cache_lengths = [len(beam) - 1 for beam in beams]
            cache = cache_fn(cache, cache_mask, cache_lengths)  # type: ignore

            input_ids = torch.tensor(
                [beam.last_token_id for beam in beams],
                device=device,
            ).unsqueeze(-1)
            position_ids = torch.tensor(
                cache_lengths,
                device=device,
            ).unsqueeze(-1)
            max_cache_length = max(cache_lengths) + 1
            pad_mask = torch.tensor(
                [
                    [False] * (max_cache_length - len(beam)) + [True] * len(beam)
                    for beam in beams
                ],
                device=device,
            )
        else:
            input_ids = pad_sequence(
                [torch.tensor(beam.token_ids) for beam in beams],
                batch_first=True,
                padding_value=pad_token_id,
                padding_side="left",
            ).to(device)
            pad_mask = input_ids != pad_token_id
            position_ids = torch.cumsum(pad_mask, -1) - 1
            position_ids[~pad_mask] = 0

            if cache is not None:
                # clear cache
                cache = None
                torch.cuda.empty_cache()

        logits, cache = decode_fn(input_ids, position_ids, pad_mask, cache)
        log_probs = torch.log_softmax(logits, dim=-1)

        # apply logit functions
        for logit_fn in logit_fns or []:
            logits = logit_fn(logits, beams)

        selected_ids, selected_logits = sample_fn(logits, beam_width)
        # filter out invalid ids by checking logits for -inf
        # (prob = 0 after softmax)
        valid_ids = torch.logical_not(torch.isneginf(selected_logits))

        batch_candidates: list[list[Beam]] = [[] for _ in range(batch_size)]

        for i, batch_idx in enumerate(indices):
            beam = beams[i]
            # set cache index for beam
            beam.cache = i

            for token_id in selected_ids[i, valid_ids[i]]:
                if single:
                    candidate = beam
                else:
                    # must clone here when beam_width > 1
                    candidate = beam.clone()

                token_id = int(token_id.item())
                candidate.add(token_id, log_probs[i, token_id].item())
                batch_candidates[batch_idx].append(candidate)

        for batch_idx, candidates in enumerate(batch_candidates):
            # reset current beams and fill with best candidates
            current_beams[batch_idx] = []

            # score and sort candidates
            candidates = sorted(candidates, key=score_fn, reverse=True)

            for candidate in candidates:
                # update candidates
                candidate = update_fn(candidate)
                if candidate is None:
                    # skip invalid candidates
                    continue

                current_beams[batch_idx].append(candidate)
                if len(current_beams[batch_idx]) >= beam_width:
                    break

        beams, indices = filter_beams()

        if yield_intermediate:
            yield get_outputs()

    return get_outputs()
