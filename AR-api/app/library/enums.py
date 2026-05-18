from enum import Enum


class LibrarySortBy(str, Enum):
    TIME = "time"
    NAME = "name"
    SIZE = "size"


class LibrarySortDirection(str, Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


class LibraryDownloadSourceScope(str, Enum):
    BROWSE = "browse"
    DETAIL = "detail"
