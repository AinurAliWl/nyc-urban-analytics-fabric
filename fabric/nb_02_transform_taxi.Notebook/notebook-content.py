# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# PARAMETERS CELL ********************

source_year = 2024
source_month = 1

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from datetime import date

import notebookutils
from pyspark.sql import functions as F

source_year = int(source_year)
source_month = int(source_month)

month_start = date(source_year, source_month, 1)

if source_month == 12:
    next_month_start = date(source_year + 1, 1, 1)
else:
    next_month_start = date(source_year, source_month + 1, 1)

source_file = (
    f"yellow_tripdata_{source_year}-{source_month:02d}.parquet"
)

bronze_info = notebookutils.lakehouse.get("lh_bronze")
silver_info = notebookutils.lakehouse.get("lh_silver")

bronze_root = bronze_info["properties"]["abfsPath"].rstrip("/")
silver_root = silver_info["properties"]["abfsPath"].rstrip("/")

bronze_file_path = (
    f"{bronze_root}/Files/nyc_taxi/yellow/"
    f"{source_year}/{source_month:02d}/{source_file}"
)

silver_table_path = f"{silver_root}/Tables/dbo/taxi_trips"

if not notebookutils.fs.exists(bronze_file_path):
    raise FileNotFoundError(f"Source file not found: {bronze_file_path}")

df_taxi_raw = spark.read.parquet(bronze_file_path)

print(f"Source file: {source_file}")
print(f"Month start: {month_start}")
print(f"Next month start: {next_month_start}")
print(f"Source rows: {df_taxi_raw.count():,}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Keep one copy of each fully identical source row.
df_taxi_unique = df_taxi_raw.dropDuplicates()

df_taxi_silver = (
    df_taxi_unique
    .withColumn(
        "pickup_date",
        F.to_date("tpep_pickup_datetime")
    )
    .withColumn(
        "trip_duration_seconds",
        F.expr(
            "timestampdiff(SECOND, "
            "tpep_pickup_datetime, tpep_dropoff_datetime)"
        )
    )
    .withColumn(
        "is_outside_source_month",
        F.coalesce(
            ~(
                (F.col("pickup_date") >= F.lit(month_start))
                & (F.col("pickup_date") < F.lit(next_month_start))
            ),
            F.lit(True)
        )
    )
    .withColumn(
        "has_invalid_duration",
        F.col("trip_duration_seconds").isNull()
        | (F.col("trip_duration_seconds") <= 0)
    )
    .withColumn(
        "has_invalid_distance",
        F.col("trip_distance").isNull()
        | (F.col("trip_distance") <= 0)
    )
    .withColumn(
        "has_negative_total",
        F.coalesce(F.col("total_amount") < 0, F.lit(False))
    )
    .withColumn(
        "has_missing_passenger_count",
        F.col("passenger_count").isNull()
    )
    .withColumn("source_year", F.lit(source_year))
    .withColumn("source_month", F.lit(source_month))
    .withColumn("source_file", F.lit(source_file))
)

expected_rows = df_taxi_silver.count()

if expected_rows == 0:
    raise ValueError("Prepared dataset is empty. Silver write cancelled.")

print(f"Prepared rows: {expected_rows:,}")
print(f"Prepared columns: {len(df_taxi_silver.columns)}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from delta.tables import DeltaTable

if DeltaTable.isDeltaTable(spark, silver_table_path):
    target_schema = spark.read.format("delta").load(silver_table_path).schema

    source_vendor_type = df_taxi_silver.schema["VendorID"].dataType.simpleString()
    target_vendor_type = target_schema["VendorID"].dataType.simpleString()
    print(f"VendorID type: {source_vendor_type} -> {target_vendor_type}")

    df_taxi_silver = df_taxi_silver.to(target_schema)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

month_condition = (
    f"source_year = {source_year} "
    f"AND source_month = {source_month}"
)

(
    df_taxi_silver.write
    .format("delta")
    .mode("overwrite")
    .option("replaceWhere", month_condition)
    .option("delta.feature.timestampNtz", "supported")
    .partitionBy("source_year", "source_month")
    .save(silver_table_path)
)

df_saved_month = (
    spark.read
    .format("delta")
    .load(silver_table_path)
    .filter(
        (F.col("source_year") == source_year)
        & (F.col("source_month") == source_month)
    )
)

saved_rows = df_saved_month.count()

if saved_rows != expected_rows:
    raise RuntimeError(
        f"Row count mismatch: expected {expected_rows}, "
        f"but found {saved_rows} in Silver."
    )

print("Silver transformation completed successfully.")
print(f"Source month: {source_year}-{source_month:02d}")
print(f"Expected rows: {expected_rows:,}")
print(f"Saved rows: {saved_rows:,}")
print(f"Saved columns: {len(df_saved_month.columns)}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
