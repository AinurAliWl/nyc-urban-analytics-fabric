-- Run in wh_gold to verify one valid EUR/USD rate per calendar day.
SELECT
    d.calendar_year,
    COUNT(DISTINCT d.date_key) AS calendar_days,
    COUNT_BIG(fx.date_key) AS fx_rows,
    COUNT(DISTINCT CASE
        WHEN fx.usd_per_eur > 0
         AND fx.rate_source_date <= d.calendar_date
        THEN d.date_key
    END) AS days_with_valid_fx,
    MAX(CASE WHEN MONTH(d.calendar_date) = 1 AND DAY(d.calendar_date) = 1
        THEN fx.rate_source_date END) AS jan_01_rate_source_date,
    MAX(CASE WHEN MONTH(d.calendar_date) = 1 AND DAY(d.calendar_date) = 1
        THEN fx.usd_per_eur END) AS jan_01_usd_per_eur
FROM dbo.DimDate AS d
LEFT JOIN dbo.DimFX AS fx
    ON fx.date_key = d.date_key
   AND fx.base_currency = 'EUR'
   AND fx.quote_currency = 'USD'
GROUP BY d.calendar_year
ORDER BY d.calendar_year;

SELECT
    COUNT(*) AS gdp_rows,
    COUNT(gdp_usd) AS years_with_value,
    MIN(gdp_year) AS first_year,
    MAX(gdp_year) AS last_year
FROM dbo.DimGDP;
