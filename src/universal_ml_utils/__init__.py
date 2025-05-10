from importlib import metadata

try:
    __version__ = metadata.version("universal_ml_utils")
except metadata.PackageNotFoundError:
    __version__ = "unknown"
