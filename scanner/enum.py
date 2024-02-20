from enum import StrEnum


class FileType(StrEnum):
    UNKNOWN = "unknown"
    PDF = "pdf"
    JPG = "jpg"
    PNG = "png"
    GIF = "gif"
    HEIC = "heic"

    @classmethod
    def _missing_(self, value):
        if value == "jpeg":
            return FileType.JPG

        return FileType.UNKNOWN

    def suffix(self) -> str:
        return f".{self}"
