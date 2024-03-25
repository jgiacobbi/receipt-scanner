import logging
from pathlib import Path
from typing import Iterable

from .enum import FileType
from .record import Record


class Scanner:
    """Reads image file metadata in the source directory."""

    def __init__(self, source_dir: Path, confidence: float):
        self.source_dir = source_dir
        self.confidence = confidence
        self.logger = logging.getLogger()
        self.records_path = source_dir / "records.csv"
        self.__known_records: dict[str, Record] = {}

    @property
    def known_records(self) -> dict[str, Record]:
        if not self.__known_records:
            if self.records_path.exists():
                with self.records_path.open() as f:
                    self.__known_records = Record.parse_csv(f.read())

        return self.__known_records

    def scan(self) -> Iterable[Record]:
        """Scan for files that need to be processed

        Returns:
            dict[str, Record]: A dictionary of records keyed by filename
        """
        self.logger.info(f"Loading images from {self.source_dir}")

        for file in self.source_dir.iterdir():
            logline = f"{file}... "

            if not file.is_file():
                logline += "not a file, skipping"
                self.logger.info(logline)
                continue

            filetype = self.guess_file_type(file)
            if filetype == FileType.CSV:
                continue

            if filetype == FileType.UNKNOWN:
                logline += "unknown file type, skipping"
                self.logger.info(logline)
                continue

            if known := self.known_records.get(file.name):
                if known.confidence >= self.confidence:
                    logline += f"known record with high confidence ({known.confidence}), skipping"
                    self.logger.info(logline)
                    continue
                else:
                    logline += f"known record with low confidence ({known.confidence}), processing"
                    self.logger.info(logline)
                    yield known
            else:
                self.logger.info(logline)
                yield Record(file.name, filetype)

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
