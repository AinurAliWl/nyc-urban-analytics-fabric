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
# MAGIC     AND a.sensor_id = 673
# MAGIC     AND a.pollutant = 'pm25'
# MAGIC     AND a.has_invalid_daily_mean = 0
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
