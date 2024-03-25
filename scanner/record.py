from dataclasses import dataclass
from datetime import date as pydate
import uuid
from .enum import FileType
from typing import Iterable, Self


@dataclass
class Record:
    """A transaction record"""

    filename: str
    filetype: FileType = None
    date: pydate = None
    name: str = None
    total: float = None
    tax: float = None
    confidence: float = None

    def short_date(self) -> str:
        return self.date.strftime("%m%d%Y")

    def short_name(self) -> str:
        return self.name.strip().replace(" ", "").lower()

    def needs_new_filename(self, confidence: float) -> bool:
        if self.confidence < confidence:
            return False

        parts = self.filename.split("_")
        if len(parts) != 3:
            return True

        date, name, _ = parts
        if not (date == self.short_date() and name == self.short_name()):
            return True

        return False

    def generate_new_filename(self, confidence: float):
        if self.needs_new_filename(confidence):
            self.filename = f"{self.short_date()}_{self.short_name()}_{uuid.uuid4().hex[:8]}{self.filetype.suffix()}"

    def __format__(self) -> str:
        return f"({self.name}, {self.total}, {self.confidence})"

    def __str__(self) -> str:
        return ",".join(
            [
                str(self.date),
                self.name,
                str(self.total),
                str(self.tax),
                str(self.confidence),
                self.filename,
            ]
        )

    @classmethod
    def header(cls) -> str:
        return ",".join(["date", "name", "total", "tax", "confidence", "filename"])

    @classmethod
    def generate_csv(self, records: Iterable[Self]) -> str:
        header = self.header()
        return header + "\n" + "\n".join([str(record) for record in records])

    @classmethod
    def parse_csv(cls, csv: str) -> dict[str, Self]:
        lines = csv.strip().split("\n")
        if lines[0] != cls.header():
            raise ValueError("Invalid CSV header")

        records = [cls.from_csv(line) for line in lines[1:] if line.strip() != ""]
        return {record.filename: record for record in records}

    @classmethod
    def from_csv(cls, line: str):
        date, name, total, tax, confidence, filename = line.strip().split(",")
        return cls(
            filename,
            FileType(filename.split(".")[-1]),
            pydate.fromisoformat(date),
            name,
            float(total),
            float(tax),
            float(confidence),
        )
