import logging
from pathlib import Path
from typing import Iterable

from .enum import FileType


class Loader:
    """Reads image files in the source directoy and returns their content and file type."""

    def __init__(self, source_dir: Path):
        self.source_dir = source_dir
        self.logger = logging.getLogger()

    def load(self) -> Iterable[tuple[Path, bytes, FileType]]:
        self.logger.info(f"Loading images from {self.source_dir}")
        for file in self.source_dir.iterdir():
            logline = f"{file}... "

            if not file.is_file():
                logline += "not a file, skipping"
                self.logger.info(logline)
                continue

            filetype = self.guess_file_type(file)
            if filetype == FileType.UNKNOWN:
                logline += "unknown file type, skipping"
                self.logger.info(logline)
                continue

            yield file, file.read_bytes(), filetype

    def guess_file_type(self, file: Path) -> FileType:
        filetype = FileType(file.suffix[1:])

        if filetype == FileType.UNKNOWN:
            with file.open("rb") as f:
                header = f.read(16)
                filetype = self.read_magic_number(header)
                f.seek(0)

        return filetype

    def read_magic_number(self, header: bytes) -> FileType:
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return FileType.PNG
        elif header.startswith(b"\xff\xd8\xff"):
            return FileType.JPG
        elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return FileType.GIF
        elif header.startswith(b"%PDF-"):
            return FileType.PDF
        elif header[4:12] == b"ftypheic":
            return FileType.HEIC
        else:
            return FileType.UNKNOWN
