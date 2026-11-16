# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "warehouse": {
# META       "default_warehouse": "46faeaf7-8901-49f0-a3e5-edcaf0b8e5c7",
# META       "known_warehouses": [
# META         {
# META           "id": "46faeaf7-8901-49f0-a3e5-edcaf0b8e5c7",
# META           "type": "Lakewarehouse"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

taxi_path = "abfss://ff9401b1-9897-44bb-a371-52cdaf97b9b3@onelake.dfs.fabric.microsoft.com/3f4301b6-a76f-414c-93e6-ce42e8b7d5b0/Files/nyc_taxi/yellow/2024/01/yellow_tripdata_2024-01.parquet"

df_taxi = spark.read.parquet(taxi_path)

df_taxi.printSchema()

display(df_taxi.limit(10))


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

display(
    df_taxi.agg(
        F.count("*").alias("row_count"),
        F.min("tpep_pickup_datetime").alias("earliest_pickup"),
        F.max("tpep_pickup_datetime").alias("latest_pickup")
    )
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

pickup = F.col("tpep_pickup_datetime")

month_start = F.lit("2024-01-01 00:00:00").cast("timestamp_ntz")
next_month_start = F.lit("2024-02-01 00:00:00").cast("timestamp_ntz")

df_taxi_dates = df_taxi.withColumn(
    "pickup_period",
    F.when(pickup.isNull(), "missing_date")
     .when(pickup < month_start, "before_january")
     .when(pickup >= next_month_start, "after_january")
     .otherwise("within_january")
)

display(
    df_taxi_dates
    .groupBy("pickup_period")
    .agg(
        F.count("*").alias("row_count"),
        F.min("tpep_pickup_datetime").alias("earliest_pickup"),
        F.max("tpep_pickup_datetime").alias("latest_pickup")
    )
    .orderBy("pickup_period")
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

quality_summary = df_taxi.agg(
    F.count(
        F.when(F.col("tpep_dropoff_datetime").isNull(), 1)
    ).alias("missing_dropoff"),

    F.count(
        F.when(
            F.col("tpep_dropoff_datetime") <= F.col("tpep_pickup_datetime"),
            1
        )
    ).alias("dropoff_not_after_pickup"),

    F.count(
        F.when(F.col("trip_distance").isNull(), 1)
    ).alias("missing_distance"),

    F.count(
        F.when(F.col("trip_distance") <= 0, 1)
    ).alias("zero_or_negative_distance"),

    F.count(
        F.when(F.col("total_amount").isNull(), 1)
    ).alias("missing_total_amount"),

    F.count(
        F.when(F.col("total_amount") < 0, 1)
    ).alias("negative_total_amount"),

    F.count(
        F.when(F.col("passenger_count").isNull(), 1)
    ).alias("missing_passenger_count")
)

quality_summary.show(vertical=True, truncate=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

display(
    df_taxi
    .filter(F.col("total_amount") < 0)
    .groupBy("payment_type")
    .agg(
        F.count("*").alias("negative_rows"),
        F.min("total_amount").alias("min_total"),
        F.max("total_amount").alias("max_total")
    )
    .orderBy(F.desc("negative_rows"))
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

total_rows = df_taxi.count()

unique_rows = df_taxi.dropDuplicates().count()

duplicate_rows = total_rows - unique_rows

print(f"Total rows: {total_rows:,}")
print(f"Unique rows: {unique_rows:,}")
print(f"Duplicate rows: {duplicate_rows:,}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

df_taxi_prepared = (
    df_taxi
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
)

display(
    df_taxi_prepared.select(
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "pickup_date",
        "trip_duration_seconds",
        "trip_distance",
        "total_amount"
    ).limit(10)
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

source_month_start = F.lit("2024-01-01").cast("date")
next_month_start = F.lit("2024-02-01").cast("date")

within_source_month = (
    (F.col("pickup_date") >= source_month_start)
    & (F.col("pickup_date") < next_month_start)
)

df_taxi_flagged = (
    df_taxi_prepared
    .withColumn(
        "is_outside_source_month",
        F.coalesce(~within_source_month, F.lit(True))
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
)

flag_columns = [
    "is_outside_source_month",
    "has_invalid_duration",
    "has_invalid_distance",
    "has_negative_total",
    "has_missing_passenger_count"
]

flag_summary = df_taxi_flagged.agg(
    *[
        F.count(F.when(F.col(name), 1)).alias(name)
        for name in flag_columns
    ]
)

flag_summary.show(vertical=True, truncate=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import notebookutils

silver_info = notebookutils.lakehouse.get("lh_silver")

print(silver_info)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F

source_year = 2024
source_month = 1
source_file = "yellow_tripdata_2024-01.parquet"

silver_root = silver_info["properties"]["abfsPath"].rstrip("/")
silver_table_path = f"{silver_root}/Tables/dbo/taxi_trips"

df_taxi_silver = (
    df_taxi_flagged
    .withColumn("source_year", F.lit(source_year))
    .withColumn("source_month", F.lit(source_month))
    .withColumn("source_file", F.lit(source_file))
)

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

print("Silver table saved successfully.")
print(f"Source month: {source_year}-{source_month:02d}")
print(f"Table path: {silver_table_path}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df_silver_check = (
    spark.read
    .format("delta")
    .load(silver_table_path)
    .filter(
        (F.col("source_year") == source_year)
        & (F.col("source_month") == source_month)
    )
)

print(f"Saved rows for this source month: {df_silver_check.count():,}")
print(f"Saved columns: {len(df_silver_check.columns)}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import notebookutils
from pyspark.sql import functions as F

silver_info = notebookutils.lakehouse.get("lh_silver")
silver_root = silver_info["properties"]["abfsPath"].rstrip("/")

df_silver_check = (
    spark.read
    .format("delta")
    .load(f"{silver_root}/Tables/dbo/taxi_trips")
)

(
    df_silver_check
    .groupBy("source_year", "source_month", "source_file")
    .agg(F.count("*").alias("row_count"))
    .orderBy("source_year", "source_month", "source_file")
    .show(truncate=False)
)

print(f"Saved columns: {len(df_silver_check.columns)}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
