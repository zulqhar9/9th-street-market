-- Month-by-month return of every ticker, from month-end closes.
WITH month_end AS (
    SELECT ticker,
           strftime('%Y-%m', date) AS month,
           close,
           ROW_NUMBER() OVER (PARTITION BY ticker, strftime('%Y-%m', date)
                              ORDER BY date DESC) AS rn
      FROM prices
)
SELECT ticker,
       month,
       ROUND(close / LAG(close) OVER (PARTITION BY ticker ORDER BY month) - 1, 4) AS monthly_return
  FROM month_end
 WHERE rn = 1
 ORDER BY ticker, month;
