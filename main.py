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

    def run(self):
        filetypes: dict[Path, FileType] = {}
        results: dict[Path, Record] = {}
        dupes: dict[str, Path] = {}

        self.logger.info(f"Using source directory {self.args.source_dir}")

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
                newname = record.new_filename(file.stem)
                newpath = file.with_name(newname).with_suffix(filetypes[file].suffix())

                if newpath != file:
                    file.rename(newpath)
                    self.logger.info(f"Renamed {file} to {newpath}")
                else:
                    self.logger.info(f"Skipped renaming {file}")

        csv = "\n".join([str(record) for record in results.values()]) + "\n"

        if self.args.write:
            self.logger.info("Writing records to file")
            (self.args.source_dir / "records.csv").write_text(csv)
            self.logger.info(f"Wrote records to {self.args.source_dir / 'records.csv'}")
        else:
            self.logger.info("Records:")
            print()
            print(csv)

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
