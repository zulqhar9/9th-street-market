"""Refresh the stock lists the website uses.

India: NSE's public archives. US: Nasdaq Trader's public symbol directory (Nasdaq, NYSE and
other US exchanges). Run occasionally (the NIFTY 50 is rebalanced twice a year):
    python scripts/update_stock_lists.py
"""
import csv
import io
import re
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SOURCES = {
    "nifty50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    "equities": "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
    "nasdaq": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "other_us": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; 9th-street-market/1.0)"}
US_EXCHANGES = {"N": "NYSE", "A": "NYSE American", "P": "NYSE Arca", "Z": "Cboe", "V": "IEX"}
# Not ordinary shares: skip warrants, units, rights, preferred shares, notes and similar.
NOT_COMMON = re.compile(r"\b(warrants?|units?|rights?|preferred|preference|notes?|debentures?|"
                        r"subordinated|trust preferred|% )\b", re.IGNORECASE)


def download(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as resp:
        return resp.read().decode("utf-8-sig")


def fetch(url: str, delimiter: str = ",") -> list[dict[str, str]]:
    rows = csv.DictReader(io.StringIO(download(url)), delimiter=delimiter)
    return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in rows]


def write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"Wrote {len(rows):,} rows to {path.relative_to(DATA.parent)}")


def us_name(full: str) -> str:
    """'Alphabet Inc. - Class A Common Stock' -> 'Alphabet Inc. Class A'; 'Apple Inc. - Common Stock' -> 'Apple Inc.'"""
    adr = bool(re.search(r"American Depositary", full, re.IGNORECASE))
    name = re.split(r"\s+-\s+", full, maxsplit=1)[0]
    name = re.sub(r"\s+American Depositary (Shares|Receipts?)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(New\s+)?(Class [A-Z]\s+)?(Common Stock|Ordinary Shares|Common Shares)\b.*$", "", name,
                  flags=re.IGNORECASE).strip()
    share_class = re.search(r"\bClass ([A-Z])\b", full)
    if share_class and "Class" not in name:
        name += f" Class {share_class.group(1)}"
    return name + (" ADR" if adr else "")


def us_equities() -> list[list[str]]:
    rows = {}
    for r in fetch(SOURCES["nasdaq"], "|"):
        if r.get("Symbol", "").startswith("File Creation"):
            continue
        if r["ETF"] == "N" and r["Test Issue"] == "N" and not NOT_COMMON.search(r["Security Name"]):
            rows[r["Symbol"]] = [r["Symbol"], us_name(r["Security Name"]), "NASDAQ"]
    for r in fetch(SOURCES["other_us"], "|"):
        if r.get("ACT Symbol", "").startswith("File Creation"):
            continue
        if r["ETF"] == "N" and r["Test Issue"] == "N" and not NOT_COMMON.search(r["Security Name"]):
            symbol = r["ACT Symbol"].replace(".", "-")  # Yahoo writes BRK.B as BRK-B
            if "$" in symbol:
                continue
            rows[symbol] = [symbol, us_name(r["Security Name"]), US_EXCHANGES.get(r["Exchange"], "US")]
    return sorted(rows.values())


def main() -> None:
    DATA.mkdir(exist_ok=True)
    nifty = fetch(SOURCES["nifty50"])
    write(DATA / "nifty50.csv", ["symbol", "name", "industry"],
          sorted([[r["Symbol"], r["Company Name"], r["Industry"]] for r in nifty]))

    equities = fetch(SOURCES["equities"])
    write(DATA / "nse_equities.csv", ["symbol", "name", "series"],
          sorted([[r["SYMBOL"], r["NAME OF COMPANY"], r["SERIES"]] for r in equities]))

    write(DATA / "us_equities.csv", ["symbol", "name", "exchange"], us_equities())


if __name__ == "__main__":
    main()
