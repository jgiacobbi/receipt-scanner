#!/usr/bin/env python3.12
import json
import logging
import logging.config
import os
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from dotenv import find_dotenv, load_dotenv

from scanner import Scanner, Client, Record


@dataclass
class Args:
    source_dir: Path
    api_key: str
    rename: bool
    write: bool
    confidence: float

    def __post_init__(self):
        self.source_dir = Path(self.source_dir)

    def validate(self):
        if not self.source_dir.exists():
            raise ValueError(f"Source directory {self.source_dir} does not exist")

        if not self.source_dir.is_dir():
            raise ValueError(f"Source directory {self.source_dir} is not a directory")

        if not self.api_key:
            raise ValueError("API Key is required")


class Main:
    def __init__(self, args: Args):
        self.args = args
        self.reader = Client(args.api_key)
        self.scanner = Scanner(args.source_dir, args.confidence)
        self.logger = logging.getLogger()

    def run(self):
        self.logger.info(f"Using source directory {self.args.source_dir}")
        self.logger.info(f"Found {len(self.scanner.known_records)} known records")

        records = self.reader.run(self.args.source_dir, list(self.scanner.scan()))

        self.logger.info(f"Processed {len(records)} records")

        if self.args.rename and records:
            self.logger.info("Renaming files")
            for record in records:
                if record.confidence < self.args.confidence:
                    self.logger.warning(
                        f"Not renaming {record.filename}, low confidence: {record.confidence}"
                    )
                else:
                    record.generate_new_filename(self.args.confidence)
                    if self.args.write:
                        file = self.args.source_dir / record.filename
                        newpath = file.parent / record.filename

                        if newpath != file:
                            file.rename(newpath)
                            self.logger.info(f"Renamed {file} to {newpath}")
                        else:
                            self.logger.info(f"Skipped renaming {file}")

        csv = self.generate_csv(records)

        if self.args.write:
            self.logger.info("Writing records to file")
            (self.args.source_dir / "records.csv").write_text(csv)
            self.logger.info(f"Wrote records to {self.args.source_dir / 'records.csv'}")
        else:
            self.logger.info("Records:")
            print()
            print(csv)

    def generate_csv(self, records: list[Record]) -> str:
        final = self.scanner.known_records.copy()
        final.update({record.filename: record for record in records})
        return Record.generate_csv(final.values())

    @classmethod
    def get_api_key(cls) -> str:
        return os.environ.get("KEY")

    @classmethod
    def parse_args(cls, argv: list[str] = None) -> Args:
        parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("--source-dir", required=True, help="Directory to scan for receipts")
        parser.add_argument(
            "--api-key",
            required=cls.get_api_key() is None,
            help="API Key for Taggun if not in env",
        )
        parser.add_argument(
            "--rename", action="store_true", help="Rename files to {date}_{vendor}_{nonce}.{type}"
        )
        parser.add_argument(
            "--write", action="store_true", help="Write records to a file in the source directory"
        )
        parser.add_argument(
            "--confidence",
            default=0.5,
            type=float,
            help="Minimum confidence level to rename files",
        )

        args = Args(**vars(parser.parse_args(argv)))

        if not args.api_key:
            args.api_key = cls.get_api_key()

        args.validate()

        return args

    @classmethod
    def setup_logger(cls):
        conig_path = Path(__file__).parent / "log_config.json"
        config = json.loads(conig_path.read_text())
        logging.config.dictConfig(config)

    @classmethod
    def from_cli(cls, argv: list[str] = None) -> Self:
        load_dotenv(find_dotenv())
        obj = cls(cls.parse_args(argv))
        cls.setup_logger()
        return obj


if __name__ == "__main__":
    Main.from_cli().run()
