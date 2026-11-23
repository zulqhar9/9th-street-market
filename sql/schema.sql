-- Daily adjusted closing prices, one row per ticker per trading day.
CREATE TABLE IF NOT EXISTS prices (
    ticker  TEXT NOT NULL,
    date    TEXT NOT NULL,          -- ISO date, YYYY-MM-DD
    close   REAL NOT NULL,          -- split/dividend-adjusted close
    volume  INTEGER,
    PRIMARY KEY (ticker, date)
);

-- The portfolio being analysed (reloaded from portfolio.csv on every run).
CREATE TABLE IF NOT EXISTS holdings (
    ticker    TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    shares    REAL NOT NULL CHECK (shares > 0),
    buy_date  TEXT NOT NULL         -- bought at the close of the first trading day on/after this date
);

CREATE INDEX IF NOT EXISTS idx_prices_date ON prices (date);
