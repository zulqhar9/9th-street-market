"""Refresh the stock lists the website uses, from NSE's public archives.

Run occasionally (the NIFTY 50 is rebalanced twice a year):
    python scripts/update_stock_lists.py
"""
import csv
import io
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SOURCES = {
    "nifty50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    "equities": "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; 9th-street-market/1.0)"}


def fetch(url: str) -> list[dict[str, str]]:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as resp:
        text = resp.read().decode("utf-8-sig")
    return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(io.StringIO(text))]


def write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"Wrote {len(rows):,} rows to {path.relative_to(DATA.parent)}")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    nifty = fetch(SOURCES["nifty50"])
    write(DATA / "nifty50.csv", ["symbol", "name", "industry"],
          sorted([[r["Symbol"], r["Company Name"], r["Industry"]] for r in nifty]))

    equities = fetch(SOURCES["equities"])
    write(DATA / "nse_equities.csv", ["symbol", "name", "series"],
          sorted([[r["SYMBOL"], r["NAME OF COMPANY"], r["SERIES"]] for r in equities]))


if __name__ == "__main__":
    main()
