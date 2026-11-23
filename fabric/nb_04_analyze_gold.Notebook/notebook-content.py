# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.12"
# META   },
# META   "dependencies": {}
# META }

# CELL ********************

# MAGIC %%tsql -artifact wh_gold -type Warehouse -bind taxi_pm25
# MAGIC WITH taxi_by_day AS (
# MAGIC     SELECT date_key, SUM(trip_count) AS trip_count
# MAGIC     FROM dbo.FactTaxiDaily
# MAGIC     GROUP BY date_key
# MAGIC )
# MAGIC SELECT
# MAGIC     d.calendar_date,
# MAGIC     t.trip_count,
# MAGIC     a.daily_mean AS pm25_ug_m3
# MAGIC FROM dbo.DimDate AS d
# MAGIC JOIN taxi_by_day AS t
# MAGIC     ON t.date_key = d.date_key
# MAGIC LEFT JOIN dbo.FactAirQualityDaily AS a
# MAGIC     ON a.date_key = d.date_key
# MAGIC    AND a.sensor_key = 'openaq:673'
# MAGIC    AND a.pollutant = 'pm25'
# MAGIC    AND a.has_invalid_daily_mean = 0
# MAGIC WHERE d.calendar_date >= '20240101'
# MAGIC   AND d.calendar_date < '20240301'
# MAGIC ORDER BY d.calendar_date;

# METADATA ********************

# META {
# META   "language": "sql",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import StrMethodFormatter

daily = pd.DataFrame(taxi_pm25).copy()
daily["calendar_date"] = pd.to_datetime(daily["calendar_date"])
daily["trip_count"] = pd.to_numeric(daily["trip_count"])
daily["pm25_ug_m3"] = pd.to_numeric(daily["pm25_ug_m3"])
daily = daily.sort_values("calendar_date")

fig, (ax_trips, ax_pm25) = plt.subplots(
    2, 1, figsize=(11, 6), sharex=True, layout="constrained"
)

ax_trips.plot(daily["calendar_date"], daily["trip_count"], color="#2563eb")
ax_trips.set_ylabel("Taxi trips")
ax_trips.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))

ax_pm25.plot(daily["calendar_date"], daily["pm25_ug_m3"], color="#15803d")
ax_pm25.set_ylabel("CCNY PM2.5 (µg/m³)")
ax_pm25.set_xlabel("New York local date")
ax_pm25.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
ax_pm25.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

for ax in (ax_trips, ax_pm25):
    ax.grid(axis="y", alpha=0.25)

fig.suptitle("NYC Yellow Taxi Trips and CCNY PM2.5 | Jan–Feb 2024")
plt.show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

pairs = daily.dropna(subset=["trip_count", "pm25_ug_m3"]).copy()
is_weekend = pairs["calendar_date"].dt.dayofweek >= 5

groups = {
    "All days": pairs,
    "Weekdays": pairs.loc[~is_weekend],
    "Weekends": pairs.loc[is_weekend],
}

results = pd.DataFrame([
    {
        "day_type": name,
        "days_with_both_values": len(group),
        "avg_daily_trips": group["trip_count"].mean(),
        "avg_pm25_ug_m3": group["pm25_ug_m3"].mean(),
        "pearson_r": group["trip_count"].corr(group["pm25_ug_m3"]),
    }
    for name, group in groups.items()
])

display(results.round({
    "avg_daily_trips": 0,
    "avg_pm25_ug_m3": 2,
    "pearson_r": 3,
}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# MAGIC %%tsql -artifact wh_gold -type Warehouse
# MAGIC 
# MAGIC WITH taxi_by_day AS (
# MAGIC     SELECT
# MAGIC         date_key,
# MAGIC         SUM(trip_count) AS trip_count,
# MAGIC         SUM(total_amount_usd) AS daily_amount_usd
# MAGIC     FROM dbo.FactTaxiDaily
# MAGIC     GROUP BY date_key
# MAGIC )
# MAGIC SELECT
# MAGIC     d.calendar_year,
# MAGIC     d.calendar_month,
# MAGIC     SUM(t.trip_count) AS trip_count,
# MAGIC     CAST(SUM(t.daily_amount_usd) AS decimal(24, 2)) AS total_amount_usd,
# MAGIC     CAST(
# MAGIC         SUM(CAST(t.daily_amount_usd AS decimal(22, 2)) / fx.usd_per_eur)
# MAGIC         AS decimal(24, 2)
# MAGIC     ) AS total_amount_eur
# MAGIC FROM taxi_by_day AS t
# MAGIC JOIN dbo.DimDate AS d
# MAGIC     ON d.date_key = t.date_key
# MAGIC JOIN dbo.DimFX AS fx
# MAGIC     ON fx.date_key = t.date_key
# MAGIC     AND fx.base_currency = 'EUR'
# MAGIC     AND fx.quote_currency = 'USD'
# MAGIC GROUP BY d.calendar_year, d.calendar_month
# MAGIC ORDER BY d.calendar_year, d.calendar_month;

# METADATA ********************

# META {
# META   "language": "sql",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# MAGIC %%tsql -artifact wh_gold -type Warehouse
# MAGIC WITH gdp_series AS (
# MAGIC     SELECT
# MAGIC         gdp_year,
# MAGIC         gdp_usd,
# MAGIC         LAG(gdp_usd) OVER (ORDER BY gdp_year) AS previous_gdp_usd
# MAGIC     FROM dbo.DimGDP
# MAGIC     WHERE country_code = 'USA'
# MAGIC       AND indicator_code = 'NY.GDP.MKTP.CD'
# MAGIC )
# MAGIC SELECT
# MAGIC     gdp_year,
# MAGIC     CAST(gdp_usd / 1000000000.0 AS decimal(12, 2)) AS gdp_usd_billions,
# MAGIC     CAST(
# MAGIC         100.0 * (gdp_usd / NULLIF(previous_gdp_usd, 0) - 1.0)
# MAGIC         AS decimal(8, 2)
# MAGIC     ) AS nominal_gdp_yoy_pct
# MAGIC FROM gdp_series
# MAGIC WHERE gdp_year >= 2020
# MAGIC ORDER BY gdp_year;

# METADATA ********************

# META {
# META   "language": "sql",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# MAGIC %%tsql -artifact wh_gold -type Warehouse -bind taxi_borough
# MAGIC 
# MAGIC SELECT
# MAGIC     d.calendar_year,
# MAGIC     d.calendar_month,
# MAGIC     z.borough AS pickup_borough,
# MAGIC     SUM(t.trip_count) AS trip_count,
# MAGIC     CAST(
# MAGIC         SUM(t.distance_sum_miles) / NULLIF(SUM(t.valid_distance_trip_count), 0)
# MAGIC         AS decimal(10, 2)
# MAGIC     ) AS avg_distance_miles,
# MAGIC     CAST(
# MAGIC         SUM(t.duration_sum_seconds) / 60.0
# MAGIC         / NULLIF(SUM(t.valid_duration_trip_count), 0)
# MAGIC         AS decimal(10, 2)
# MAGIC     ) AS avg_duration_minutes
# MAGIC FROM dbo.FactTaxiDaily AS t
# MAGIC JOIN dbo.DimDate AS d
# MAGIC     ON d.date_key = t.date_key
# MAGIC JOIN dbo.DimZone AS z
# MAGIC     ON z.location_id = t.pickup_location_id
# MAGIC GROUP BY d.calendar_year, d.calendar_month, z.borough
# MAGIC ORDER BY d.calendar_year, d.calendar_month, trip_count DESC;

# METADATA ********************

# META {
# META   "language": "sql",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

nyc_boroughs = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"]

borough_data = pd.DataFrame(taxi_borough).copy()
borough_data["trip_count"] = pd.to_numeric(borough_data["trip_count"])

trips_by_borough = (
    borough_data.groupby("pickup_borough")["trip_count"]
    .sum()
    .reindex(nyc_boroughs, fill_value=0)
    .sort_values()
)

fig, ax = plt.subplots(figsize=(9, 4), layout="constrained")
ax.barh(trips_by_borough.index, trips_by_borough.values, color="#2563eb")
ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
ax.set_xlabel("Taxi trips")
ax.set_title("Yellow Taxi pickups by NYC borough | Jan–Feb 2024")
ax.set_axisbelow(True)
ax.grid(axis="x", alpha=0.25)
plt.show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# MAGIC %%tsql -artifact wh_gold -type Warehouse
# MAGIC WITH taxi_by_day AS (
# MAGIC     SELECT
# MAGIC         date_key,
# MAGIC         SUM(trip_count) AS trip_count,
# MAGIC         SUM(fare_sum_usd) AS fare_usd,
# MAGIC         SUM(fare_trip_count) AS fare_trip_count,
# MAGIC         SUM(total_amount_usd) AS total_usd,
# MAGIC         SUM(amount_trip_count) AS amount_trip_count
# MAGIC     FROM dbo.FactTaxiDaily
# MAGIC     GROUP BY date_key
# MAGIC )
# MAGIC SELECT
# MAGIC     d.calendar_year,
# MAGIC     d.calendar_month,
# MAGIC     SUM(t.trip_count) AS trip_count,
# MAGIC     CAST(SUM(t.fare_usd) / NULLIF(SUM(t.fare_trip_count), 0)
# MAGIC         AS decimal(12, 2)) AS avg_metered_fare_usd,
# MAGIC     CAST(SUM(t.total_usd) / NULLIF(SUM(t.amount_trip_count), 0)
# MAGIC         AS decimal(12, 2)) AS avg_total_per_trip_usd,
# MAGIC     CAST(
# MAGIC         SUM(CAST(t.total_usd AS decimal(22, 2)) / fx.usd_per_eur)
# MAGIC         / NULLIF(SUM(t.amount_trip_count), 0)
# MAGIC         AS decimal(12, 2)
# MAGIC     ) AS avg_total_per_trip_eur
# MAGIC FROM taxi_by_day AS t
# MAGIC JOIN dbo.DimDate AS d
# MAGIC     ON d.date_key = t.date_key
# MAGIC JOIN dbo.DimFX AS fx
# MAGIC     ON fx.date_key = t.date_key
# MAGIC     AND fx.base_currency = 'EUR'
# MAGIC     AND fx.quote_currency = 'USD'
# MAGIC GROUP BY d.calendar_year, d.calendar_month
# MAGIC ORDER BY d.calendar_year, d.calendar_month;

# METADATA ********************

# META {
# META   "language": "sql",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# MAGIC %%tsql -artifact wh_gold -type Warehouse
# MAGIC SELECT TOP (10)
# MAGIC     z.location_id,
# MAGIC     z.borough,
# MAGIC     z.zone_name,
# MAGIC     SUM(t.trip_count) AS pickup_count
# MAGIC FROM dbo.FactTaxiDaily AS t
# MAGIC JOIN dbo.DimZone AS z
# MAGIC     ON z.location_id = t.pickup_location_id
# MAGIC WHERE t.date_key BETWEEN 20240101 AND 20240229
# MAGIC   AND z.borough IN ('Bronx', 'Brooklyn', 'Manhattan', 'Queens', 'Staten Island')
# MAGIC GROUP BY z.location_id, z.borough, z.zone_name
# MAGIC ORDER BY pickup_count DESC, z.location_id;

# METADATA ********************

# META {
# META   "language": "sql",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# MAGIC %%tsql -artifact wh_gold -type Warehouse -bind air_year_comparison
# MAGIC WITH valid_days AS (
# MAGIC     SELECT
# MAGIC         d.calendar_year,
# MAGIC         d.calendar_month,
# MAGIC         DAY(d.calendar_date) AS day_of_month,
# MAGIC         a.sensor_key,
# MAGIC         a.station_name,
# MAGIC         a.pollutant,
# MAGIC         a.unit,
# MAGIC         a.daily_mean
# MAGIC     FROM dbo.FactAirQualityDaily AS a
# MAGIC     JOIN dbo.DimDate AS d ON d.date_key = a.date_key
# MAGIC     WHERE d.calendar_year IN (2022, 2024)
# MAGIC       AND d.calendar_month IN (1, 2)
# MAGIC       AND a.has_invalid_daily_mean = 0
# MAGIC       AND a.coverage_ratio >= 0.75
# MAGIC )
# MAGIC SELECT
# MAGIC     b.pollutant,
# MAGIC     b.unit,
# MAGIC     b.station_name,
# MAGIC     b.sensor_key,
# MAGIC     COUNT(*) AS matched_days,
# MAGIC     CAST(AVG(b.daily_mean) AS decimal(10, 2)) AS avg_2022,
# MAGIC     CAST(AVG(c.daily_mean) AS decimal(10, 2)) AS avg_2024,
# MAGIC     CAST(AVG(c.daily_mean - b.daily_mean) AS decimal(10, 2)) AS change_2024_vs_2022
# MAGIC FROM valid_days AS b
# MAGIC JOIN valid_days AS c
# MAGIC     ON c.sensor_key = b.sensor_key
# MAGIC    AND c.pollutant = b.pollutant
# MAGIC    AND c.unit = b.unit
# MAGIC    AND c.calendar_month = b.calendar_month
# MAGIC    AND c.day_of_month = b.day_of_month
# MAGIC WHERE b.calendar_year = 2022
# MAGIC   AND c.calendar_year = 2024
# MAGIC GROUP BY b.pollutant, b.unit, b.station_name, b.sensor_key
# MAGIC ORDER BY b.pollutant, b.station_name;

# METADATA ********************

# META {
# META   "language": "sql",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import matplotlib.pyplot as plt
import pandas as pd

air = pd.DataFrame(air_year_comparison).copy()

for column in ["avg_2022", "avg_2024", "matched_days"]:
    air[column] = pd.to_numeric(air[column])

fig, axes = plt.subplots(
    2, 1, figsize=(10, 6), gridspec_kw={"height_ratios": [4, 2]}
)

panels = [("no2", "NO₂ (ppb)"), ("pm25", "PM2.5 (µg/m³)")]

for ax, (pollutant, xlabel) in zip(axes, panels):
    stations = air.loc[air["pollutant"].eq(pollutant)].sort_values(
        "avg_2022", ascending=False
    )
    positions = range(len(stations))
    station_labels = [
        f"{name} (n={days})"
        for name, days in zip(stations["station_name"], stations["matched_days"])
    ]

    ax.barh(
        [y - 0.18 for y in positions], stations["avg_2022"],
        height=0.34, label="2022", color="#64748b"
    )
    ax.barh(
        [y + 0.18 for y in positions], stations["avg_2024"],
        height=0.34, label="2024", color="#2563eb"
    )
    ax.set_yticks(list(positions), station_labels)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    ax.set_axisbelow(True)
    ax.grid(axis="x", alpha=0.25)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False)
fig.suptitle("NYC air quality on matched dates | Jan–Feb 2022 and 2024")
fig.subplots_adjust(left=0.36, right=0.96, top=0.88, bottom=0.14, hspace=0.56)
plt.show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# MAGIC %%tsql -artifact wh_gold -type Warehouse -bind taxi_air_daily
# MAGIC WITH station_borough AS (
# MAGIC     SELECT 'openaq:673' AS sensor_key, 'Manhattan' AS borough
# MAGIC     UNION ALL SELECT 'openaq:1102', 'Bronx'
# MAGIC     UNION ALL SELECT 'openaq:1152', 'Queens'
# MAGIC     UNION ALL SELECT 'epa_aqs:36-005-0110-42602-1', 'Bronx'
# MAGIC     UNION ALL SELECT 'epa_aqs:36-005-0133-42602-1', 'Bronx'
# MAGIC     UNION ALL SELECT 'epa_aqs:36-081-0124-42602-1', 'Queens'
# MAGIC     UNION ALL SELECT 'epa_aqs:36-081-0125-42602-1', 'Queens'
# MAGIC ),
# MAGIC taxi_by_borough_day AS (
# MAGIC     SELECT
# MAGIC         t.date_key,
# MAGIC         z.borough,
# MAGIC         SUM(t.trip_count) AS pickup_count
# MAGIC     FROM dbo.FactTaxiDaily AS t
# MAGIC     JOIN dbo.DimZone AS z ON z.location_id = t.pickup_location_id
# MAGIC     GROUP BY t.date_key, z.borough
# MAGIC )
# MAGIC SELECT
# MAGIC     d.calendar_date,
# MAGIC     d.calendar_year,
# MAGIC     s.borough,
# MAGIC     a.station_name,
# MAGIC     a.sensor_key,
# MAGIC     a.pollutant,
# MAGIC     a.unit,
# MAGIC     t.pickup_count,
# MAGIC     a.daily_mean
# MAGIC FROM dbo.FactAirQualityDaily AS a
# MAGIC JOIN dbo.DimDate AS d ON d.date_key = a.date_key
# MAGIC JOIN station_borough AS s ON s.sensor_key = a.sensor_key
# MAGIC JOIN taxi_by_borough_day AS t
# MAGIC     ON t.date_key = a.date_key
# MAGIC    AND t.borough = s.borough
# MAGIC WHERE (
# MAGIC        a.date_key BETWEEN 20220101 AND 20220228
# MAGIC     OR a.date_key BETWEEN 20240101 AND 20240228
# MAGIC )
# MAGIC   AND a.has_invalid_daily_mean = 0
# MAGIC   AND a.coverage_ratio >= 0.75
# MAGIC ORDER BY d.calendar_year, a.pollutant, a.station_name, d.calendar_date;

# METADATA ********************

# META {
# META   "language": "sql",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import pandas as pd

paired = pd.DataFrame(taxi_air_daily).copy()
for column in ["pickup_count", "daily_mean"]:
    paired[column] = pd.to_numeric(paired[column])

paired = paired.dropna(subset=["pickup_count", "daily_mean"])

group_columns = [
    "pollutant", "unit", "borough", "station_name",
    "sensor_key", "calendar_year",
]

results = []
for key, days in paired.groupby(group_columns):
    results.append({
        **dict(zip(group_columns, key)),
        "paired_days": len(days),
        "avg_daily_pickups": days["pickup_count"].mean(),
        "avg_concentration": days["daily_mean"].mean(),
        "pearson_r": days["pickup_count"].corr(days["daily_mean"]),
    })

display(pd.DataFrame(results).round({
    "avg_daily_pickups": 0,
    "avg_concentration": 2,
    "pearson_r": 3,
}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ### Findings: Yellow Taxi pickups and air quality
# 
# We compared daily Yellow Taxi pickups in each station's borough with
# the station's daily pollutant concentration, from January 1 through
# February 28 in 2022 and 2024. Measurements needed at least 75% coverage.
# 
# The clearest positive association was for NO₂ at IS 52 in the Bronx
# (r = 0.425 in 2022 and r = 0.333 in 2024). At CCNY in Manhattan,
# the PM2.5 association was negative in 2022 (r = −0.293) and close
# to zero in 2024 (r = −0.005).
# 
# Among the six sensors present in both years, the absolute correlation
# was smaller in 2024 for every sensor. Available dates varied by sensor
# and year. These are descriptive associations between borough-level
# pickup counts and individual monitoring stations.
