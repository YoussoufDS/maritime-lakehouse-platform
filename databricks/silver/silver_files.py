# Databricks notebook source
# MAGIC %run /Workspace/Users/raissa.tchotchoua-tonou@hec.ca/Config

# COMMAND ----------

# DBTITLE 1,Install great_expectations
# MAGIC %pip install great_expectations==0.15.50

# COMMAND ----------

# CELLULE 2 — Imports
from pyspark.sql.functions import (
    current_timestamp, lit, col, trim, upper, lower,
    to_date, to_timestamp, round, year, month,
    explode, struct
)
from pyspark.sql.types import IntegerType, DoubleType, StringType
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number
import great_expectations as gx
from great_expectations.dataset import SparkDFDataset
from datetime import datetime

start_time = datetime.now()
results_dq  = []

print(f"Start : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# COMMAND ----------

# CELLULE 3 — Fonctions utilitaires
def apply_constraints(table_full_name, constraints):
    existing = spark.sql(
        f"SHOW TBLPROPERTIES {table_full_name}"
    ).filter(col("key").like("delta.constraints.%")).collect()

    for row in existing:
        cname = row["key"].replace("delta.constraints.", "")
        try:
            spark.sql(
                f"ALTER TABLE {table_full_name} "
                f"DROP CONSTRAINT IF EXISTS {cname}"
            )
        except:
            pass

    for cname, expr in constraints:
        spark.sql(
            f"ALTER TABLE {table_full_name} "
            f"ADD CONSTRAINT {cname} CHECK ({expr})"
        )
        print(f"    🔒 {cname}")


def run_ge_validation(df, table_name, expectations):
    ge_df  = SparkDFDataset(df)
    passed = 0
    failed = []
    for method, kwargs in expectations:
        result = getattr(ge_df, method)(**kwargs)
        if result["success"]:
            passed += 1
        else:
            failed.append(f"{method}({list(kwargs.values())})")
    return passed, len(expectations), failed


def write_silver(df, target_table, dedup_keys=None):
    if dedup_keys:
        w  = Window.partitionBy(dedup_keys).orderBy(
            col("_ingestion_timestamp").desc()
        )
        df = (df
            .withColumn("_rn", row_number().over(w))
            .filter(col("_rn") == 1)
            .drop("_rn")
        )
    df = (df
        .withColumn("_silver_timestamp", current_timestamp())
        .withColumn("_silver_pipeline",  lit("silver_files"))
    )
    (df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target_table)
    )
    return df, spark.table(target_table).count()

# COMMAND ----------

# CELLULE 4 — bunkering_events (CSV)
print("\n── bunkering_events_raw ──")
df = spark.table(f"{bronze_fuelops}.bunkering_events_raw")

df_silver = (df
    .withColumn("vessel_id",      col("vessel_id").cast(IntegerType()))
    .withColumn("quantity_mt",    col("quantity_mt").cast(DoubleType()))
    .withColumn("unit_price_usd", col("unit_price_usd").cast(DoubleType()))
    .withColumn("total_cost_usd", col("total_cost_usd").cast(DoubleType()))
    .withColumn("rob_before_mt",  col("rob_before_mt").cast(DoubleType()))
    .withColumn("rob_after_mt",   col("rob_after_mt").cast(DoubleType()))
    .withColumn("bunker_date",    to_date(col("bunker_date")))
    .withColumn("fuel_grade",     trim(upper(col("fuel_grade"))))
    .withColumn("port_name",      trim(upper(col("port_name"))))
    .withColumn("supplier",       trim(col("supplier")))
    .withColumn("source_system",  trim(col("source_system")))
    .filter(col("vessel_id").isNotNull())
    .filter(col("bunker_date").isNotNull())
    .filter(col("quantity_mt") > 0)
    .drop("year", "ingestion_date")
)

df_silver, cnt = write_silver(
    df_silver,
    f"{silver_fuelops}.bunkering_events_files",
    ["vessel_id", "bunker_date", "port_name", "fuel_grade"]
)
print(f"  ✅ silver_fuelops.bunkering_events_files → {cnt:,} rows")

apply_constraints(f"{silver_fuelops}.bunkering_events_files", [
    ("bef_vessel_pos",   "vessel_id > 0"),
    ("bef_qty_pos",      "quantity_mt > 0"),
    ("bef_price_pos",    "unit_price_usd > 0"),
    ("bef_cost_pos",     "total_cost_usd > 0"),
    ("bef_date_notnull", "bunker_date IS NOT NULL"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_fuelops}.bunkering_events_files"),
    "bunkering_events_files", [
        ("expect_column_values_to_not_be_null",
            {"column": "vessel_id"}),
        ("expect_column_values_to_not_be_null",
            {"column": "bunker_date"}),
        ("expect_column_values_to_be_between",
            {"column": "quantity_mt", "min_value": 0}),
        ("expect_column_values_to_be_between",
            {"column": "unit_price_usd", "min_value": 0}),
        ("expect_column_values_to_be_between",
            {"column": "total_cost_usd", "min_value": 0}),
        ("expect_column_values_to_not_be_null",
            {"column": "fuel_grade"}),
    ]
)
results_dq.append(("bunkering_events_files", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed"
      + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

# CELLULE 5 — consumption_logs (CSV)
print("\n── consumption_logs_raw ──")
df = spark.table(f"{bronze_fuelops}.consumption_logs_raw")

df_silver = (df
    .withColumn("vessel_id",      col("vessel_id").cast(IntegerType()))
    .withColumn("consumption_mt", col("consumption_mt").cast(DoubleType()))
    .withColumn("speed_knots",    col("speed_knots").cast(DoubleType()))
    .withColumn("distance_nm",    col("distance_nm").cast(DoubleType()))
    .withColumn("running_hours",  col("running_hours").cast(IntegerType()))
    .withColumn("eeoi",           col("eeoi").cast(DoubleType()))
    .withColumn("load_factor",    col("load_factor").cast(DoubleType()))
    .withColumn("log_date",       to_date(col("log_date")))
    .withColumn("fuel_grade",     trim(upper(col("fuel_grade"))))
    .withColumn("sea_condition",  trim(lower(col("sea_condition"))))
    .withColumn("source_system",  trim(col("source_system")))
    .withColumn("efficiency_mt_nm",
        round(
            col("consumption_mt") / col("distance_nm"), 4
        )
    )
    .filter(col("vessel_id").isNotNull())
    .filter(col("log_date").isNotNull())
    .filter(col("consumption_mt") > 0)
    .filter(col("distance_nm") > 0)
    .drop("year", "month", "ingestion_date")
)

df_silver, cnt = write_silver(
    df_silver,
    f"{silver_fuelops}.consumption_logs",
    ["vessel_id", "log_date", "fuel_grade"]
)
print(f"  ✅ silver_fuelops.consumption_logs → {cnt:,} rows")

apply_constraints(f"{silver_fuelops}.consumption_logs", [
    ("cl_vessel_pos",     "vessel_id > 0"),
    ("cl_cons_pos",       "consumption_mt > 0"),
    ("cl_dist_pos",       "distance_nm > 0"),
    ("cl_date_notnull",   "log_date IS NOT NULL"),
    ("cl_speed_valid",    "speed_knots > 0 AND speed_knots <= 50"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_fuelops}.consumption_logs"),
    "consumption_logs", [
        ("expect_column_values_to_not_be_null",
            {"column": "vessel_id"}),
        ("expect_column_values_to_not_be_null",
            {"column": "log_date"}),
        ("expect_column_values_to_be_between",
            {"column": "consumption_mt", "min_value": 0}),
        ("expect_column_values_to_be_between",
            {"column": "distance_nm", "min_value": 0}),
        ("expect_column_values_to_be_between",
            {"column": "speed_knots", "min_value": 0, "max_value": 50}),
        ("expect_column_values_to_not_be_null",
            {"column": "fuel_grade"}),
        ("expect_column_values_to_not_be_null",
            {"column": "efficiency_mt_nm"}),
    ]
)
results_dq.append(("consumption_logs", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed"
      + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

# CELLULE 6 — weather_raw (JSON nested → explode)
print("\n── weather_raw ──")
df = spark.table(f"{bronze_navigation}.weather_raw")

# Exploser le array records
df_exploded = df.select(explode(col("records")).alias("rec"))

df_silver = (df_exploded
    .select(
        col("rec.zone_name").alias("zone_name"),
        col("rec.latitude").alias("latitude"),
        col("rec.longitude").alias("longitude"),
        col("rec.wind_speed_knots").alias("wind_speed_knots"),
        col("rec.wind_direction").alias("wind_direction"),
        col("rec.wave_height_m").alias("wave_height_m"),
        col("rec.current_knots").alias("current_knots"),
        col("rec.temp_celsius").alias("temp_celsius"),
        col("rec.visibility_nm").alias("visibility_nm"),
        col("rec.pressure_hpa").alias("pressure_hpa"),
        col("rec.precipitation").alias("precipitation"),
        col("rec.sea_state").alias("sea_state"),
        col("rec.report_timestamp").alias("report_timestamp"),
        col("rec.source").alias("source"),
        col("rec.ingestion_date").alias("ingestion_date"),
    )
    .withColumn("latitude",         col("latitude").cast(DoubleType()))
    .withColumn("longitude",        col("longitude").cast(DoubleType()))
    .withColumn("wind_speed_knots", col("wind_speed_knots").cast(DoubleType()))
    .withColumn("wave_height_m",    col("wave_height_m").cast(DoubleType()))
    .withColumn("current_knots",    col("current_knots").cast(DoubleType()))
    .withColumn("temp_celsius",     col("temp_celsius").cast(DoubleType()))
    .withColumn("visibility_nm",    col("visibility_nm").cast(DoubleType()))
    .withColumn("pressure_hpa",     col("pressure_hpa").cast(DoubleType()))
    .withColumn("report_timestamp", to_timestamp(col("report_timestamp")))
    .withColumn("zone_name",        trim(col("zone_name")))
    .withColumn("wind_direction",   trim(col("wind_direction")))
    .withColumn("precipitation",    trim(lower(col("precipitation"))))
    .withColumn("sea_state",        trim(lower(col("sea_state"))))
    .filter(col("report_timestamp").isNotNull())
    .filter(col("zone_name").isNotNull())
    .filter(col("latitude").between(-90, 90))
    .filter(col("longitude").between(-180, 180))
    .dropDuplicates(["zone_name", "report_timestamp"])
)

df_silver, cnt = write_silver(
    df_silver,
    f"{silver_navigation}.weather",
    None
)
print(f"  ✅ silver_navigation.weather → {cnt:,} rows")

apply_constraints(f"{silver_navigation}.weather", [
    ("wx_lat_valid",   "latitude BETWEEN -90 AND 90"),
    ("wx_lon_valid",   "longitude BETWEEN -180 AND 180"),
    ("wx_wind_pos",    "wind_speed_knots >= 0"),
    ("wx_wave_pos",    "wave_height_m >= 0"),
    ("wx_zone_notnull","zone_name IS NOT NULL"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_navigation}.weather"),
    "weather", [
        ("expect_column_values_to_not_be_null",
            {"column": "zone_name"}),
        ("expect_column_values_to_not_be_null",
            {"column": "report_timestamp"}),
        ("expect_column_values_to_be_between",
            {"column": "latitude", "min_value": -90, "max_value": 90}),
        ("expect_column_values_to_be_between",
            {"column": "longitude", "min_value": -180, "max_value": 180}),
        ("expect_column_values_to_be_between",
            {"column": "wind_speed_knots", "min_value": 0}),
        ("expect_column_values_to_be_between",
            {"column": "wave_height_m", "min_value": 0}),
        ("expect_column_values_to_be_between",
            {"column": "temp_celsius", "min_value": -50, "max_value": 60}),
    ]
)
results_dq.append(("weather", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed"
      + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

# CELLULE 7 — Résumé DQ
end_time     = datetime.now()
duration     = (end_time - start_time).seconds
total_rows   = sum(r[1] for r in results_dq)
total_checks = sum(r[3] for r in results_dq)
total_passed = sum(r[2] for r in results_dq)
total_failed = total_checks - total_passed

print("\n" + "=" * 60)
print("  silver_files — Data Quality Summary")
print("=" * 60)
print(f"  {'Table':<30} {'Rows':>8}  {'GE':>10}  Status")
print("-" * 60)
for tbl, rows, passed, total, failed in results_dq:
    status = "✅" if not failed else "⚠️"
    print(f"  {tbl:<30} {rows:>8,}  {passed}/{total} checks  {status}")
print("-" * 60)
print(f"  {'TOTAL':<30} {total_rows:>8,}  "
      f"{total_passed}/{total_checks} checks")
print(f"  Duration  : {duration}s")
print(f"  Ended     : {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

if total_failed > 0:
    print("\n  ⚠️  Checks échoués :")
    for tbl, rows, passed, total, failed in results_dq:
        if failed:
            print(f"    → {tbl} : {failed}")