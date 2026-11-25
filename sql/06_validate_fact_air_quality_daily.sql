-- Run in wh_gold to check the daily grain and coverage of the air-quality fact.
WITH sensor_days AS (
    SELECT
        d.calendar_year,
        f.source_system,
        f.pollutant,
        f.unit,
        f.sensor_key,
        f.date_key,
        COUNT_BIG(*) AS rows_per_day
    FROM dbo.FactAirQualityDaily AS f
    JOIN dbo.DimDate AS d ON d.date_key = f.date_key
    GROUP BY
        d.calendar_year, f.source_system, f.pollutant, f.unit,
        f.sensor_key, f.date_key
)
SELECT
    calendar_year,
    source_system,
    pollutant,
    unit,
    SUM(rows_per_day) AS fact_rows,
    COUNT(DISTINCT sensor_key) AS sensors_loaded,
    SUM(rows_per_day - 1) AS duplicate_rows
FROM sensor_days
GROUP BY calendar_year, source_system, pollutant, unit
ORDER BY calendar_year, pollutant;
