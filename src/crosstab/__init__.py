from importlib.metadata import PackageNotFoundError, version

from .crosstab import (
    Crosstab,
    __author__,
    __author_email__,
    __description__,
    __license__,
    __title__,
    __url__,
)

try:
    __version__ = version("crosstab")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"

__all__ = [
    "Crosstab",
    "__author__",
    "__author_email__",
    "__description__",
    "__license__",
    "__title__",
    "__url__",
    "__version__",
]
