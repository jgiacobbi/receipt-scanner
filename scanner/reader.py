import json
from contextlib import contextmanager

import requests
from datetime import date as pydate
from dateutil.parser import parse as date_parse

from .record import Record


class Reader:
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
        self.__session = None

    @property
    def headers(self) -> dict:
        return {"accept": "application/json", "apikey": self.api_key}

    @contextmanager
    def session(self):
        self.__session = requests.Session()

        try:
            yield self
        finally:
            self.__session.close()

    def process_receipt(self, file: bytes, record: Record) -> Record:
        files = {"file": (record.filename, file, f"image/{record.filetype}")}
        if self.__session:
            response = self.__session.post(
                self.url, data=self.payload, headers=self.headers, files=files
            )
        else:
            response = requests.post(
                self.url, data=self.payload, headers=self.headers, files=files
            )

        if response.status_code != 200:
            raise Exception(f"Failed to process receipt: {response.text}")

        response = json.loads(response.text)

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

        confidence = response["confidenceLevel"]

        record.date = date
        record.name = merchant_name
        record.total = total_amount
        record.tax = tax_amount
        record.confidence = confidence

        return record
