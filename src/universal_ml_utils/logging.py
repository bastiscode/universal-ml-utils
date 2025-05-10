import logging

LOG_FORMAT = "[%(asctime)s] {%(name)s - %(levelname)s} %(message)s"


def setup_logging(level: str | int | None = None) -> None:
    """

    Sets up logging with a custom log format and level.

    :param level: log level
    :return: None
    """
    logging.basicConfig(format=LOG_FORMAT, level=level)


def disable_logging() -> None:
    """

    Disables logging.

    :return: None
    """
    logging.disable(logging.CRITICAL)


def add_file_log(logger: logging.Logger, log_file: str) -> None:
    """

    Add file logging to an existing logger

    :param logger: logger
    :param log_file: path to logfile
    :return: logger with file logging handler
    """
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)


def get_logger(name: str, level: str | int | None = None) -> logging.Logger:
    """

    Get a logger that writes to stderr.

    :param name: name of the logger
    :param level: log level
    :return: logger
    """

    logger = logging.getLogger(name)
    logger.propagate = False
    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    if not logger.hasHandlers():
        logger.addHandler(stderr_handler)

    logger.setLevel(level or logging.root.level)

    return logger
