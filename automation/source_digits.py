"""Download UCI Optical Recognition of Handwritten Digits and retain one row per class."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
URL = "https://archive.ics.uci.edu/static/public/80/optical+recognition+of+handwritten+digits.zip"


def discover(out):
    with urlopen(URL, timeout=60) as response:
        archive = response.read()
    with ZipFile(io.BytesIO(archive)) as packed:
        member = next(s for s in packed.namelist() if s.endswith("optdigits.tra"))
        raw = packed.read(member)
    selected = {}
    rows = list(csv.reader(raw.decode().splitlines()))
    for index, row in enumerate(rows, 1):
        assert len(row) == 65
        digit = row[-1].strip()
        if digit not in selected:
            selected[digit] = dict(row=index, pixels=list(map(int, row[:-1])))
    assert set(selected) == set("0123456789")
    result = dict(source=URL, doi="10.24432/C50P49", license="CC BY 4.0",
                  authors="E. Alpaydin and C. Kaynak", member=member,
                  member_sha256=hashlib.sha256(raw).hexdigest(), rows_scanned=len(rows), digits=selected)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Discovered {len(rows)} training rows, retained the first labeled sample of each digit.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "data/digits.json")
    discover(parser.parse_args().out)
