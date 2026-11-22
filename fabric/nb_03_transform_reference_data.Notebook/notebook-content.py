# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "6efa6296-f5ce-4652-9e2f-a9d7ce14b70e",
# META       "default_lakehouse_name": "lh_silver",
# META       "default_lakehouse_workspace_id": "ff9401b1-9897-44bb-a371-52cdaf97b9b3",
# META       "known_lakehouses": [
# META         {
# META           "id": "6efa6296-f5ce-4652-9e2f-a9d7ce14b70e"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

bronze_root = notebookutils.lakehouse.get("lh_bronze")["properties"]["abfsPath"].rstrip("/")


def read_bronze_table(table_name):
    return spark.read.format("delta").load(f"{bronze_root}/Tables/dbo/{table_name}")


df_air_raw = read_bronze_table("openaq_daily_raw")
df_gdp_raw = read_bronze_table("worldbank_gdp_raw")
df_fx_raw = read_bronze_table("ecb_fx_daily_raw")
df_zones_raw = read_bronze_table("taxi_zones_raw")

print("Bronze tables loaded.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

sources = [
    ("OpenAQ", df_air_raw, ["sensor_id", "local_date"]),
    ("World Bank GDP", df_gdp_raw, ["country_code", "indicator_code", "gdp_year"]),
    ("ECB FX", df_fx_raw, ["base_currency", "quote_currency", "fx_date"]),
    ("Taxi Zones", df_zones_raw, ["LocationID"]),
]

for name, df, key_columns in sources:
    result = df.agg(
        F.count("*").alias("rows"),
        F.countDistinct(*key_columns).alias("distinct_keys"),
    ).first()

    print(f"{name}: {result.rows:,} rows, {result.distinct_keys:,} distinct keys")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df_air = df_air_raw.select(
    F.col("local_date").cast("date").alias("local_date"),
    F.col("location_id").cast("long").alias("location_id"),
    F.col("sensor_id").cast("long").alias("sensor_id"),
    F.lower(F.trim("pollutant")).alias("pollutant"),
    F.trim("unit").alias("unit"),
    F.col("daily_mean").cast("double").alias("daily_mean"),
    F.col("observed_hours").cast("int").alias("observed_hours"),
    F.col("expected_hours").cast("int").alias("expected_hours"),
)

observed = F.col("observed_hours")
expected = F.col("expected_hours")
daily_mean = F.col("daily_mean")

df_air = (
    df_air
    .withColumn(
        "coverage_ratio",
        F.when((expected > 0) & (observed >= 0) & (observed <= expected),
               observed / expected),
    )
    .withColumn(
        "has_invalid_daily_mean",
        daily_mean.isNull() | F.isnan(daily_mean) | (daily_mean < 0),
    )
)

df_gdp = df_gdp_raw.select(
    F.upper(F.trim("country_code")).alias("country_code"),
    F.trim("country_name").alias("country_name"),
    F.trim("indicator_code").alias("indicator_code"),
    F.col("gdp_year").cast("int").alias("gdp_year"),
    F.col("gdp_usd").cast("decimal(20,2)").alias("gdp_usd"),
)

df_fx = df_fx_raw.select(
    F.col("fx_date").cast("date").alias("fx_date"),
    F.upper(F.trim("base_currency")).alias("base_currency"),
    F.upper(F.trim("quote_currency")).alias("quote_currency"),
    F.col("usd_per_eur").cast("decimal(18,8)").alias("usd_per_eur"),
)

df_zones = df_zones_raw.select(
    F.col("LocationID").cast("int").alias("location_id"),
    F.trim("Borough").alias("borough"),
    F.trim("Zone").alias("zone_name"),
    F.trim("service_zone").alias("service_zone"),
)

df_air.orderBy("local_date").show(5, truncate=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

silver_tables = [
    ("air_quality_daily", df_air, ["sensor_id", "local_date"]),
    ("gdp_annual", df_gdp, ["country_code", "indicator_code", "gdp_year"]),
    ("fx_rates_daily", df_fx, ["base_currency", "quote_currency", "fx_date"]),
    ("taxi_zones", df_zones, ["location_id"]),
]

validated_rows = {}

for table_name, df, key_columns in silver_tables:
    result = df.agg(
        F.count("*").alias("rows"),
        F.countDistinct(*key_columns).alias("distinct_keys"),
    ).first()

    if result.rows == 0 or result.rows != result.distinct_keys:
        raise ValueError(
            f"{table_name}: {result.rows} rows, "
            f"{result.distinct_keys} distinct keys. Check for null or duplicate keys."
        )

    validated_rows[table_name] = result.rows
    print(f"{table_name}: {result.rows:,} rows, {result.distinct_keys:,} distinct keys")

invalid_fx = df_fx.where(
    F.col("usd_per_eur").isNull() | (F.col("usd_per_eur") <= 0)
).count()
if invalid_fx:
    raise ValueError(f"fx_rates_daily: {invalid_fx} missing or non-positive rates.")

print("Silver validation passed.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

silver_root = notebookutils.lakehouse.get("lh_silver")["properties"]["abfsPath"].rstrip("/")

for table_name, df, _ in silver_tables:
    table_path = f"{silver_root}/Tables/dbo/{table_name}"

    df.write.format("delta").mode("overwrite").save(table_path)

    saved_rows = spark.read.format("delta").load(table_path).count()
    if saved_rows != validated_rows[table_name]:
        raise ValueError(
            f"{table_name}: expected {validated_rows[table_name]:,} rows, "
            f"found {saved_rows:,} after writing."
        )

    print(f"Saved lh_silver.dbo.{table_name}: {saved_rows:,} rows")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

epa_raw = spark.table("lh_bronze.dbo.epa_no2_daily_raw")
target_table = "lh_silver.dbo.epa_no2_daily"

expected_format = (
    (F.col("parameter_code") == "42602")
    & (F.col("sample_duration") == "1 HOUR")
    & (F.col("units_of_measure") == "Parts per billion")
)
if epa_raw.where(~F.coalesce(expected_format, F.lit(False))).limit(1).count():
    raise ValueError("Expected EPA NO2 hourly observations summarized in ppb.")

epa_silver = (
    epa_raw.select(
        F.to_date("date_local", "yyyy-MM-dd").alias("local_date"),
        F.concat_ws("-", "state_code", "county_code", "site_num").alias("aqs_site_id"),
        F.col("parameter_code"),
        F.col("poc"),
        F.col("local_site_name").alias("station_name"),
        F.col("county_name"),
        F.col("latitude").cast("double").alias("latitude"),
        F.col("longitude").cast("double").alias("longitude"),
        F.lit("epa_aqs").alias("source_system"),
        F.lit("no2").alias("pollutant"),
        F.lit("ppb").alias("unit"),
        F.col("arithmetic_mean").cast("double").alias("daily_mean"),
        F.col("observation_count").cast("int").alias("observed_hours"),
        F.lit(24).alias("expected_hours"),
        F.col("source_file"),
    )
    .withColumn(
        "sensor_key",
        F.concat_ws("-", "aqs_site_id", "parameter_code", "poc"),
    )
    .withColumn("coverage_ratio", F.col("observed_hours") / F.col("expected_hours"))
    .withColumn("has_low_coverage", F.col("observed_hours") < 18)
    .withColumn(
        "has_invalid_daily_mean",
        F.col("daily_mean").isNull()
        | F.isnan("daily_mean")
        | (F.col("daily_mean") < 0),
    )
)

checks = epa_silver.agg(
    F.count("*").alias("rows"),
    F.countDistinct("sensor_key", "local_date").alias("unique_keys"),
).first()

if checks.rows == 0 or checks.rows != checks.unique_keys:
    raise ValueError("EPA NO2 is empty or has duplicate or missing sensor-date keys.")

epa_silver.write.format("delta").mode("overwrite").saveAsTable(target_table)

display(
    spark.table(target_table)
    .groupBy(F.year("local_date").alias("year"))
    .agg(
        F.count("*").alias("rows_saved"),
        F.countDistinct("aqs_site_id").alias("stations"),
        F.sum(F.col("has_low_coverage").cast("int")).alias("low_coverage_days"),
    )
    .orderBy("year")
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
