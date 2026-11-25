-- Run in wh_gold to check the daily grain and coverage of the air-quality fact.
WITH sensor_days AS (
    SELECT
        d.calendar_year,
        f.source_system,
        f.pollutant,
        f.unit,
        f.sensor_key,
        f.date_key,
        COUNT_BIG(*) AS rows_per_day,
        COUNT_BIG(CASE
            WHEN f.daily_mean IS NULL OR f.has_invalid_daily_mean = 1 THEN 1
        END) AS invalid_daily_mean_rows,
        COUNT_BIG(CASE
            WHEN f.coverage_ratio >= 0.75 AND f.daily_mean IS NOT NULL
                AND f.has_invalid_daily_mean = 0 THEN 1
        END) AS rows_with_valid_mean_and_coverage
    FROM dbo.FactAirQualityDaily AS f
    LEFT JOIN dbo.DimDate AS d ON d.date_key = f.date_key
    GROUP BY
        d.calendar_year, f.source_system, f.pollutant, f.unit,
        f.sensor_key, f.date_key
)
SELECT
    calendar_year,
    source_system,
    pollutant,
    unit,
    COUNT(DISTINCT sensor_key) AS sensor_count,
    COUNT(DISTINCT date_key) AS days_with_records,
    COUNT_BIG(*) AS sensor_days,
    SUM(rows_per_day) AS fact_rows,
    COUNT_BIG(CASE WHEN rows_per_day > 1 THEN 1 END) AS duplicate_sensor_days,
    SUM(invalid_daily_mean_rows) AS invalid_daily_mean_rows,
    SUM(rows_with_valid_mean_and_coverage) AS rows_with_valid_mean_and_coverage,
    SUM(CASE WHEN sensor_key IS NULL THEN rows_per_day ELSE 0 END) AS rows_without_sensor_key,
    SUM(CASE WHEN calendar_year IS NULL THEN rows_per_day ELSE 0 END) AS rows_without_calendar_date
FROM sensor_days
GROUP BY calendar_year, source_system, pollutant, unit
ORDER BY calendar_year, source_system, pollutant, unit;
