-- Run in wh_gold to verify one valid EUR/USD rate per calendar day.
WITH rates_by_day AS (
    SELECT
        d.calendar_year,
        d.calendar_month,
        d.day_of_month,
        d.calendar_date,
        COUNT_BIG(fx.date_key) AS fx_rows,
        COUNT_BIG(CASE
            WHEN fx.usd_per_eur > 0 AND fx.rate_source_date <= d.calendar_date THEN 1
        END) AS valid_fx_rows,
        MAX(fx.rate_source_date) AS rate_source_date,
        MAX(fx.usd_per_eur) AS usd_per_eur
    FROM dbo.DimDate AS d
    LEFT JOIN dbo.DimFX AS fx
        ON fx.date_key = d.date_key
        AND fx.base_currency = 'EUR'
        AND fx.quote_currency = 'USD'
    GROUP BY d.calendar_year, d.calendar_month, d.day_of_month, d.calendar_date
)
SELECT
    calendar_year,
    COUNT_BIG(*) AS calendar_days,
    SUM(fx_rows) AS fx_rows,
    COUNT_BIG(CASE WHEN valid_fx_rows > 0 THEN 1 END) AS days_with_valid_fx,
    COUNT_BIG(CASE WHEN fx_rows = 0 THEN 1 END) AS days_without_fx,
    COUNT_BIG(CASE WHEN fx_rows > 1 THEN 1 END) AS days_with_duplicate_fx,
    COUNT_BIG(CASE WHEN valid_fx_rows < fx_rows THEN 1 END) AS days_with_invalid_fx,
    MAX(CASE WHEN calendar_month = 1 AND day_of_month = 1
        THEN rate_source_date END) AS jan_01_rate_source_date,
    MAX(CASE WHEN calendar_month = 1 AND day_of_month = 1
        THEN usd_per_eur END) AS jan_01_usd_per_eur
FROM rates_by_day
GROUP BY calendar_year
ORDER BY calendar_year;
