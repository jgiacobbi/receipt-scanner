import aiofiles
import asyncio
import json
from pathlib import Path
from typing import Iterable

import grequests
from datetime import date as pydate
from dateutil.parser import parse as date_parse

from .record import Record


class Client:
    """Hit taggun's API to process receipt images into records."""

    url = "https://api.taggun.io/api/receipt/v1/verbose/file"

    payload = {
        "refresh": "true",
        "incognito": "true",
        "extractTime": "false",
        "extractLineItems": "false",
        "language": "en",
    }

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def headers(self) -> dict:
        return {"accept": "application/json", "apikey": self.api_key}

    def run(self, source_dir: Path, records: list[Record]) -> Iterable[Record]:
        return asyncio.run(self.run_async(source_dir, records))

    async def run_async(self, source_dir: Path, records: Record):
        tasks = [self.gen_requests(source_dir, record) for record in records]
        completed = await asyncio.gather(*tasks)

        reqs = []
        for args in completed:
            reqs.append(grequests.post(self.url, **args))

        map = list(zip(reqs, records))

        results = []

        for idx, response in grequests.imap_enumerated(reqs, size=10):
            if not response:
                print(f"Failed to process {map[idx][1].filename}")
            else:
                results.append(self.process_response(json.loads(response.text), map[idx][1]))

        return results

    async def gen_requests(self, source_dir: Path, record: Record) -> dict:
        async with aiofiles.open(source_dir / record.filename, "rb") as f:
            content = await f.read()

        return {
            "files": {"file": (record.filename, content, f"image/{record.filetype}")},
            "data": self.payload,
            "headers": self.headers,
        }

    def process_response(self, response: dict, record: Record) -> Record:
        try:
            tax_amount = response["taxAmount"]["data"]
        except:
            tax_amount = float("nan")

        try:
            total_amount = response["totalAmount"]["data"]
        except:
            total_amount = float("nan")

        try:
            merchant_name = response["merchantName"]["data"]
        except:
            merchant_name = "Unknown"

        try:
            date = date_parse(response["date"]["data"]).date()
        except:
            date = pydate.fromisoformat("0001-01-01")

        try:
            confidence = response["confidenceLevel"]
        except:
            confidence = 0.0

        record.date = date
        record.name = merchant_name
        record.total = total_amount
        record.tax = tax_amount
        record.confidence = confidence

        return record
