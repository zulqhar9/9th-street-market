-- Current value and gain/loss of every holding.
-- Buy price = close on the first trading day on/after buy_date.
WITH buy AS (
    SELECT h.ticker,
           h.name,
           h.shares,
           h.buy_date,
           (SELECT p.close
              FROM prices p
             WHERE p.ticker = h.ticker
               AND p.date >= h.buy_date
             ORDER BY p.date
             LIMIT 1) AS buy_price
      FROM holdings h
),
latest AS (
    SELECT ticker, close AS last_price, date AS last_date
      FROM (SELECT ticker, close, date,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
              FROM prices)
     WHERE rn = 1
)
SELECT b.ticker,
       b.name,
       b.shares,
       b.buy_date,
       ROUND(b.buy_price, 2)                              AS buy_price,
       ROUND(l.last_price, 2)                             AS last_price,
       l.last_date,
       ROUND(b.shares * b.buy_price, 2)                   AS cost,
       ROUND(b.shares * l.last_price, 2)                  AS market_value,
       ROUND(b.shares * (l.last_price - b.buy_price), 2)  AS gain,
       ROUND(l.last_price / b.buy_price - 1, 4)           AS total_return
  FROM buy b
  JOIN latest l USING (ticker)
 WHERE b.buy_price IS NOT NULL
 ORDER BY market_value DESC;
