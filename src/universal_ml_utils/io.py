import json
import os
from typing import Any, Iterable


def create_dir_from_file(path: str) -> str:
    """

    Creates a directory from a file path.

    :param path: path to the file
    :return: directory of the file
    """
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    return os.path.abspath(dir_path)


def load_lines(path: str) -> list[str]:
    """

    Loads lines from a file.

    :param path: path to the file
    :return: list of lines
    """
    text = []
    with open(path, "r", encoding="utf8") as inf:
        for line in inf:
            text.append(line.rstrip("\r\n"))
    return text


def dump_lines(lines: Iterable[str], path: str):
    """

    Dumps lines to a file.

    :param lines: iterable of lines
    :param path: path to the file
    """
    create_dir_from_file(path)
    with open(path, "w", encoding="utf8") as outf:
        for line in lines:
            outf.write(line + "\n")


def load_jsonl(path: str) -> list:
    """

    Loads a JSONL file.

    :param path: path to the file
    :return: list of JSON objects
    """
    data = []
    with open(path, "r", encoding="utf8") as inf:
        for line in inf:
            data.append(json.loads(line.rstrip("\r\n")))
    return data


def dump_jsonl(items: Iterable, path: str):
    """

    Dumps a list of JSON objects to a file.

    :param items: iterable of JSON objects
    :param path: path to the file
    """
    create_dir_from_file(path)
    with open(path, "w", encoding="utf8") as outf:
        for item in items:
            outf.write(json.dumps(item) + "\n")


def load_json(path: str) -> dict:
    """

    Loads a JSON file.

    :param path: path to the file
    :return: JSON object
    """
    with open(path, "r", encoding="utf8") as inf:
        return json.load(inf)


def dump_json(data: Any, path: str, **kwargs: Any):
    """

    Dumps a JSON object to a file.
    :param data: JSON object
    :param path: path to the file
    """
    create_dir_from_file(path)
    with open(path, "w", encoding="utf8") as outf:
        json.dump(data, outf, **kwargs)
