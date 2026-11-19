# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
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
