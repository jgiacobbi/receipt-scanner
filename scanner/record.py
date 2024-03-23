from dataclasses import dataclass
from datetime import date as pydate
import uuid


@dataclass
class Record:
    """A transaction record"""

    date: pydate
    name: str
    total: float
    tax: float
    confidence: float
    filename: str = None

    def __post_init__(self):
        self.generate_filename()

    def short_date(self) -> str:
        return self.date.strftime("%m%d%Y")

    def short_name(self) -> str:
        return self.name.strip().replace(" ", "").lower()

    def needs_new_filename(self) -> bool:
        if self.confidence < 0.8:
            return False

        if self.filename is None:
            return True

        parts = self.filename.split("_")
        if len(parts) != 3:
            return True

        date, name, _ = parts
        if not (date == self.short_date() and name == self.short_name()):
            return True

        return False

    def generate_filename(self):
        if self.needs_new_filename():
            self.filename = f"{self.short_date()}_{self.short_name()}_{uuid.uuid4().hex[:8]}"

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
