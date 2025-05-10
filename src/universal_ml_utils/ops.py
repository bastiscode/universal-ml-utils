from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Generator, Iterable, Iterator, TypeVar

I = TypeVar("I")  # noqa
O = TypeVar("O")  # noqa
R = TypeVar("R")


def run_parallel(
    fn: Callable[[I], O],
    inputs: Iterable[I],
    n: int | None = None,
) -> Iterator[O]:
    """

    Run a function in parallel using a thread pool.

    :param fn: function to run
    :param inputs: iterable of inputs
    :param n: number of threads to use
    :return: iterator of results
    """
    with ThreadPoolExecutor(max_workers=n) as executor:
        futures = []
        for input in inputs:
            future = executor.submit(fn, *input)
            futures.append(future)

        for future in futures:
            yield future.result()


def flatten(iter: Iterable[Iterable[I]]) -> Iterator[I]:
    """

    Flatten an iterable of iterables.

    :param iter: iterable of iterables of items
    :return: iterator of items
    """
    for sub_iter in iter:
        yield from sub_iter


def enumerate_flatten(iter: Iterable[Iterable[I]]) -> Iterator[tuple[int, I]]:
    """

    Enumerate and flatten an iterable of iterables, where the index refers
    to the outer iterable.

    :param iter: iterable of iterables of items
    :return: iterator of tuples (index, item)
    """

    for i, sub_iter in enumerate(iter):
        for item in sub_iter:
            yield i, item


def batch(items: Iterable[I], batch_size: int) -> Iterator[list[I]]:
    """

    Split an iterable into batches of a given size.

    :param items: iterable of items
    :param batch_size: size of each batch
    """
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def split(items: list[I], split: int | list[int]) -> list[list[I]]:
    """

    Split a list into sublists of given sizes.

    :param items: list of items
    :param split: size of each sublist or list of sizes
    :return: list of sublists
    """
    if isinstance(split, int):
        assert len(items) % split == 0, "split does not divide items evenly"
        split = [split] * (len(items) // split)
    else:
        assert sum(split) == len(items), "split sum does not match items length"

    start = 0
    result = []
    for step in split:
        result.append(items[start : start + step])
        start += step
    return result


def partition_by(
    iter: Iterable[I],
    key: Callable[[I], bool],
) -> tuple[list[I], list[I]]:
    """

    Partition an iterable into two lists based on a key function.
    :param iter: iterable of items
    :param key: function that returns True or False for each item
    :return: tuple of two lists
    """
    a, b = [], []
    for item in iter:
        if key(item):
            a.append(item)
        else:
            b.append(item)
    return a, b


def map_generator(
    f: Callable[[I], O],
    gen: Generator[I, None, R],
) -> Generator[O, None, R]:
    """

    Map a function over a generator.

    :param f: function to apply
    :param gen: generator to apply the function to
    :return: generator of results
    """
    try:
        while True:
            yield f(next(gen))
    except StopIteration as e:
        return e.value


def consume_generator(gen: Generator[Any, None, R]) -> R:
    """

    Consume a generator until it is exhausted and return the final value.

    :param gen: generator to consume
    :return: final value of the generator
    """
    try:
        while True:
            next(gen)
    except StopIteration as e:
        return e.value


def extract_fields(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """

    Extract fields from a dictionary.

    :param data: dictionary to extract fields from
    :param fields: list of fields to extract
    :return: dictionary of extracted fields
    """
    return {field: extract_field(data, field) for field in fields}


def extract_field(data: dict[str, Any], field: str) -> Any | None:
    """

    Extract a field from a dictionary, allowing for nested fields
    and list indexing.

    :param data: dictionary to extract field from
    :param field: field to extract
    :return: value of the field or None if not found
    """
    for key in field.split("."):
        if (
            key.startswith("[")
            and key.endswith("]")
            and all(c.isdigit() for c in key[1:-1])
        ):
            idx = int(key[1:-1])
            if not isinstance(data, list) or idx < -len(data) or idx >= len(data):
                return None
            data = data[idx]

        elif key not in data:
            return None

        else:
            data = data[key]

    return data
