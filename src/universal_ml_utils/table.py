import math

from termcolor import colored


def generate_table(
    data: list[list[str]],
    headers: list[list[str]] | None = None,
    alignments: list[str] | None = None,
    horizontal_lines: list[int] | None = None,
    highlight: set[tuple[int, int]] | None = None,
    highlight_type: str = "markdown",
    highlight_color: str = "green",
    max_column_width: int = 48,
) -> str:
    """

    Generates a table from the given data.

    :param data: data to be displayed in the table
    :param headers: headers for the table
    :param alignments: alignments for the table columns
    :param horizontal_lines: where to draw horizontal lines
    :param highlight: cells to be highlighted
    :param highlight_type: type of highlighting (markdown or terminal)
    :param highlight_color: color of the highlight
    :param max_column_width: maximum width of the columns
    :return: formatted table as a string
    """
    rows = len(data)
    if rows:
        columns = len(data[0])
    elif headers:
        columns = len(headers[0])
    else:
        return ""

    assert all(len(r) == columns for r in data), f"all rows must have {columns} columns"

    if alignments is None:
        alignments = ["left"] + ["right"] * (columns - 1)

    if highlight is None:
        highlight = set()

    max_column_width = max(10, max_column_width)
    if len(highlight) > 0 and highlight_type == "markdown":
        max_column_width += 4

    # get max width for each column in headers and data
    column_widths = []
    for i in range(columns):
        # add 4 to width if cell is bold because of the two **s left and right
        header_width = max(len(h[i]) for h in headers) if headers else 0
        data_width = max(
            min(
                max_column_width,
                len(d[i])
                + (4 * ((j, i) in highlight and highlight_type == "markdown")),
            )
            for j, d in enumerate(data)
        )
        column_widths.append(
            min(
                max_column_width,
                max(
                    # markdown needs at least three - for a proper horizontal line
                    3,
                    header_width,
                    data_width,
                ),
            )
        )

    if horizontal_lines is None:
        horizontal_lines = [0] * len(data)

    highlight_cells = [
        [(i, j) in highlight for j in range(len(data[i]))] for i in range(len(data))
    ]

    tables_lines = []

    if headers is not None:
        assert all(
            len(h) == columns for h in headers
        ), f"all headers must have {columns} columns"
        tables_lines.extend(
            [
                _table_row(
                    header,
                    [False] * columns,
                    highlight_type,
                    highlight_color,
                    alignments,
                    column_widths,
                    max_column_width,
                )
                + (
                    _table_horizontal_line(column_widths)
                    if i == len(headers) - 1
                    else ""
                )
                for i, header in enumerate(headers)
            ]
        )

    for item, horizontal_line, bold in zip(data, horizontal_lines, highlight_cells):
        line = _table_row(
            item,
            bold,
            highlight_type,
            highlight_color,
            alignments,
            column_widths,
            max_column_width,
        )
        if horizontal_line > 0:
            line += _table_horizontal_line(column_widths)
        tables_lines.append(line)

    return "\n".join(tables_lines)


def _table_cell(s: str, alignment: str, width: int) -> str:
    if alignment == "left":
        s = s.ljust(width)
    elif alignment == "right":
        s = s.rjust(width)
    else:
        s = s.center(width)
    return s


def _highlight(s: str, hcolor: str) -> str:
    return colored(s, hcolor, attrs=["bold"])  # type: ignore


def _table_row(
    data: list[str],
    highlight: list[bool],
    highlight_type: str,
    highlight_color: str,
    alignments: list[str],
    widths: list[int],
    max_width: int,
) -> str:
    num_lines = [math.ceil(len(d) / max_width) for d in data]
    max_num_lines = max(num_lines)
    lines = []
    for i in range(max_num_lines):
        line_data = [d[i * max_width : (i + 1) * max_width] for d in data]
        cells = []
        for d, h, a, w in zip(line_data, highlight, alignments, widths):
            if h and highlight_type == "markdown":
                cell = _table_cell(f"**{d}**", a, w)
            elif h and highlight_type == "terminal":
                cell = _highlight(_table_cell(d, a, w), highlight_color)
            else:
                cell = _table_cell(d, a, w)
            cells.append(cell)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _table_horizontal_line(widths: list[int]) -> str:
    return "\n| " + " | ".join("-" * w for w in widths) + " |"
