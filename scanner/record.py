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

    def short_date(self) -> str:
        return self.date.strftime("%m%d%Y")

    def short_name(self) -> str:
        return self.name.strip().replace(" ", "").lower()

    def new_filename(self, old_filename: str) -> str:
        parts = old_filename.split("_")
        if len(parts) != 3:
            return self.filename()

        date, name, _ = parts
        if date == self.short_date() and name == self.short_name():
            return old_filename

        return self.filename()

    def filename(self) -> str:
        return f"{self.short_date()}_{self.short_name()}_{uuid.uuid4().hex[:8]}"

    def __str__(self) -> str:
        return ",".join([str(self.date), self.name, str(self.total), str(self.tax)])
