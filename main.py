#!/usr/bin/env python3.12
import hashlib
import json
import logging
import logging.config
import os
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from dotenv import find_dotenv, load_dotenv

from scanner import FileType, Loader, Reader, Record


@dataclass
class Args:
    source_dir: Path
    api_key: str
    rename: bool
    write: bool
    confidence: float
    reconcile: bool
    missing: bool

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
        self.reader = Reader(args.api_key)
        self.loader = Loader(args.source_dir)
        self.logger = logging.getLogger()
        self.__known_records: dict[str, Record] = {}

    @property
    def known_records(self) -> dict[str, Record]:
        if not self.__known_records:
            records_path = self.args.source_dir / "records.csv"
            if records_path.exists():
                with records_path.open() as f:
                    self.__known_records = Record.parse_csv(f.read())
                    self.__known_records = {
                        record.filename: record for record in self.__known_records
                    }
        return self.__known_records

    def read_low_confidence_records(self) -> set[str]:
        return set(k for k, v in self.known_records.items() if v.confidence < self.args.confidence)

    def read_missing_records(self) -> set[str]:
        file_list = set(
            Path(file.name).stem for file in self.args.source_dir.iterdir() if file.is_file()
        )
        return file_list - set(self.known_records.keys())

    def run(self):
        filetypes: dict[Path, FileType] = {}
        results: dict[Path, Record] = {}
        dupes: dict[str, Path] = {}

        self.logger.info(f"Using source directory {self.args.source_dir}")
        if self.args.reconcile:
            records = self.read_low_confidence_records()
            if records:
                self.logger.info(f"Reconciling with {records}")
                self.loader.filter |= records
            else:
                self.logger.info("No low confidence records found")
                return

        elif self.args.missing:
            records = self.read_missing_records()
            if records:
                self.logger.info(f"Processing only missing records {records}")
                self.loader.filter |= records
            else:
                self.logger.info("No missing records found")
                return

        with self.reader.session():
            for path, content, ftype in self.loader.load():
                hash = hashlib.sha256(content).hexdigest()
                if hash in dupes:
                    self.logger.warning(f"Skipping {path} as it is a duplicate of {dupes[hash]}")
                    continue
                else:
                    dupes[hash] = path

                try:
                    results[path] = self.reader.process_receipt(path.name, content, ftype)
                    filetypes[path] = ftype
                except Exception as e:
                    self.logger.error(f"Failed to process {path.name}: {e}")
                    continue

        if self.args.rename and results:
            self.logger.info("Renaming files")
            for file, record in results.items():
                if record.confidence < self.args.confidence:
                    self.logger.warning(
                        f"Not renaming {file}, low confidence: {record.confidence}"
                    )
                else:
                    record.generate_new_filename()
                    newpath = file.with_name(record.filename).with_suffix(filetypes[file].suffix())

                    if newpath != file:
                        file.rename(newpath)
                        self.logger.info(f"Renamed {file} to {newpath}")
                    else:
                        self.logger.info(f"Skipped renaming {file}")

        csv = self.generate_csv(results.values())

        if self.args.write:
            self.logger.info("Writing records to file")
            (self.args.source_dir / "records.csv").write_text(csv)
            self.logger.info(f"Wrote records to {self.args.source_dir / 'records.csv'}")
        else:
            self.logger.info("Records:")
            print()
            print(csv)

    def generate_csv(self, records: list[Record]) -> str:
        final = []
        if self.args.reconcile:
            for record in records:
                if existing := self.known_records.get(record.filename):
                    if existing.confidence < record.confidence:
                        self.logger.info(f"Updating {existing} to {record}")
                        final.append(record)
                    else:
                        final.append(existing)
        elif self.args.missing:
            final = list(self.known_records.values())
            final.extend(records)
        else:
            final = records

        return "\n".join([str(record) for record in final])

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
        parser.add_argument(
            "--reconcile",
            action="store_true",
            help="Reconcile records with existing records.csv in the source directory",
        )
        parser.add_argument(
            "--missing",
            action="store_true",
            help="Only process files that are not in records.csv",
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
