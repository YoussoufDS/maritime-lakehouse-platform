# Databricks notebook source
# MAGIC %run /Workspace/Users/raissa.tchotchoua-tonou@hec.ca/Config

# COMMAND ----------

# DBTITLE 1,Install great_expectations
# MAGIC %pip install great_expectations==0.15.50

# COMMAND ----------

# CELLULE 2 — Imports
from pyspark.sql.functions import (
    current_timestamp, lit, col, trim, upper, lower,
    to_date, to_timestamp, when, coalesce,
    row_number, round, year, month, quarter
)
from pyspark.sql.window import Window
from pyspark.sql.types import (
    IntegerType, DoubleType, StringType, DateType
)
from datetime import datetime
import great_expectations as gx
from great_expectations.dataset import SparkDFDataset

start_time = datetime.now()
results_dq  = []

print(f"Start : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)


# COMMAND ----------

# CELLULE 3 — Fonctions utilitaires
def apply_constraints(table_full_name, constraints):
    """
    Applique des Delta CHECK constraints sur une table Silver.
    constraints = list of (constraint_name, sql_expression)
    """
    # Supprimer les constraints existantes d'abord
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

    # Ajouter les nouvelles constraints
    for cname, expr in constraints:
        spark.sql(
            f"ALTER TABLE {table_full_name} "
            f"ADD CONSTRAINT {cname} CHECK ({expr})"
        )
        print(f"    🔒 Constraint : {cname}")


def run_ge_validation(df, table_name, expectations):
    """
    Exécute Great Expectations sur un DataFrame Spark.
    expectations = list of (method_name, kwargs)
    Retourne (passed, total, failed_list)
    """
    ge_df    = SparkDFDataset(df)
    passed   = 0
    failed   = []

    for method, kwargs in expectations:
        result = getattr(ge_df, method)(**kwargs)
        if result["success"]:
            passed += 1
        else:
            failed.append(f"{method}({kwargs})")

    total = len(expectations)
    return passed, total, failed


def write_silver(df, target_table, dedup_key=None):
    """Déduplication + écriture Delta Silver."""
    if dedup_key:
        w  = Window.partitionBy(dedup_key).orderBy(
            col("_ingestion_timestamp").desc()
        )
        df = (df
            .withColumn("_rn", row_number().over(w))
            .filter(col("_rn") == 1)
            .drop("_rn")
        )

    df = (df
        .withColumn("_silver_timestamp", current_timestamp())
        .withColumn("_silver_pipeline",  lit("silver_erp"))
    )

    (df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target_table)
    )
    return df, spark.table(target_table).count()


# COMMAND ----------

print("\n── vessels ──")
df = spark.table(f"{bronze_fleet}.vessels")

df_silver = (df
    .withColumn("vessel_id",       col("vessel_id").cast(IntegerType()))
    .withColumn("class_id",        col("class_id").cast(IntegerType()))
    .withColumn("build_year",      col("build_year").cast(IntegerType()))
    .withColumn("deadweight_tons", col("deadweight_tons").cast(DoubleType()))
    .withColumn("teu_capacity",    col("teu_capacity").cast(IntegerType()))
    .withColumn("gross_tonnage",   col("gross_tonnage").cast(DoubleType()))
    .withColumn("vessel_name",     trim(upper(col("vessel_name"))))
    .withColumn("flag_country",    trim(upper(col("flag_country"))))
    .withColumn("status",          trim(lower(col("status"))))
    .withColumn("owner_company",   trim(col("owner_company")))
    .filter(col("vessel_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_fleet}.vessels", "vessel_id")
print(f"  ✅ silver_fleet.vessels → {cnt:,} rows")

apply_constraints(f"{silver_fleet}.vessels", [
    ("vessels_id_positive",   "vessel_id > 0"),
    ("vessels_year_valid",    "build_year >= 1900 AND build_year <= 2030"),
    ("vessels_gt_positive",   "gross_tonnage > 0"),
    ("vessels_dwt_positive",  "deadweight_tons > 0"),
    ("vessels_name_notnull",  "vessel_name IS NOT NULL"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_fleet}.vessels"), "vessels", [
        ("expect_column_values_to_not_be_null",  {"column": "vessel_id"}),
        ("expect_column_values_to_be_unique",    {"column": "vessel_id"}),
        ("expect_column_values_to_not_be_null",  {"column": "vessel_name"}),
        ("expect_column_values_to_be_between",   {"column": "build_year", "min_value": 1900, "max_value": 2030}),
        ("expect_column_values_to_be_between",   {"column": "gross_tonnage", "min_value": 0}),
        ("expect_column_values_to_be_in_set",    {"column": "status", "value_set": ["active", "inactive", "maintenance", "scrapped"]}),
    ]
)
results_dq.append(("vessels", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))


# COMMAND ----------

print("\n── vessel_classes ──")
df = spark.table(f"{bronze_fleet}.vessel_classes")

df_silver = (df
    .withColumn("class_id",        col("class_id").cast(IntegerType()))
    .withColumn("max_dwt",         col("max_dwt").cast(DoubleType()))
    .withColumn("max_teu",         col("max_teu").cast(IntegerType()))
    .withColumn("avg_speed_knots", col("avg_speed_knots").cast(DoubleType()))
    .withColumn("class_name",      trim(col("class_name")))
    .withColumn("vessel_type",     trim(col("vessel_type")))
    .filter(col("class_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_fleet}.vessel_classes", "class_id")
print(f"  ✅ silver_fleet.vessel_classes → {cnt:,} rows")

apply_constraints(f"{silver_fleet}.vessel_classes", [
    ("vc_id_positive",    "class_id > 0"),
    ("vc_speed_positive", "avg_speed_knots > 0"),
    ("vc_dwt_positive",   "max_dwt > 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_fleet}.vessel_classes"), "vessel_classes", [
        ("expect_column_values_to_not_be_null", {"column": "class_id"}),
        ("expect_column_values_to_be_unique",   {"column": "class_id"}),
        ("expect_column_values_to_not_be_null", {"column": "class_name"}),
        ("expect_column_values_to_be_between",  {"column": "avg_speed_knots", "min_value": 0, "max_value": 50}),
    ]
)
results_dq.append(("vessel_classes", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))


# COMMAND ----------

print("\n── ports ──")
df = spark.table(f"{bronze_portops}.ports")

df_silver = (df
    .withColumn("port_id",        col("port_id").cast(IntegerType()))
    .withColumn("latitude",       col("latitude").cast(DoubleType()))
    .withColumn("longitude",      col("longitude").cast(DoubleType()))
    .withColumn("max_vessel_dwt", col("max_vessel_dwt").cast(DoubleType()))
    .withColumn("port_name",      trim(upper(col("port_name"))))
    .withColumn("port_code",      trim(upper(col("port_code"))))
    .withColumn("country",        trim(upper(col("country"))))
    .withColumn("region",         trim(col("region")))
    .withColumn("port_type",      trim(col("port_type")))
    .withColumn("timezone",       trim(col("timezone")))
    .filter(col("port_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_portops}.ports", "port_id")
print(f"  ✅ silver_portops.ports → {cnt:,} rows")

apply_constraints(f"{silver_portops}.ports", [
    ("ports_id_positive",  "port_id > 0"),
    ("ports_lat_valid",    "latitude BETWEEN -90 AND 90"),
    ("ports_lon_valid",    "longitude BETWEEN -180 AND 180"),
    ("ports_name_notnull", "port_name IS NOT NULL"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_portops}.ports"), "ports", [
        ("expect_column_values_to_not_be_null", {"column": "port_id"}),
        ("expect_column_values_to_be_unique",   {"column": "port_id"}),
        ("expect_column_values_to_be_between",  {"column": "latitude", "min_value": -90, "max_value": 90}),
        ("expect_column_values_to_be_between",  {"column": "longitude", "min_value": -180, "max_value": 180}),
        ("expect_column_values_to_not_be_null", {"column": "port_name"}),
    ]
)
results_dq.append(("ports", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── terminals ──")
df = spark.table(f"{bronze_portops}.terminals")

df_silver = (df
    .withColumn("terminal_id",   col("terminal_id").cast(IntegerType()))
    .withColumn("port_id",       col("port_id").cast(IntegerType()))
    .withColumn("berth_count",   col("berth_count").cast(IntegerType()))
    .withColumn("max_depth_m",   col("max_depth_m").cast(DoubleType()))
    .withColumn("terminal_name", trim(col("terminal_name")))
    .withColumn("terminal_type", trim(col("terminal_type")))
    .filter(col("terminal_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_portops}.terminals", "terminal_id")
print(f"  ✅ silver_portops.terminals → {cnt:,} rows")

apply_constraints(f"{silver_portops}.terminals", [
    ("term_id_positive",   "terminal_id > 0"),
    ("term_port_positive", "port_id > 0"),
    ("term_depth_pos",     "max_depth_m > 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_portops}.terminals"), "terminals", [
        ("expect_column_values_to_not_be_null", {"column": "terminal_id"}),
        ("expect_column_values_to_be_unique",   {"column": "terminal_id"}),
        ("expect_column_values_to_not_be_null", {"column": "port_id"}),
        ("expect_column_values_to_be_between",  {"column": "max_depth_m", "min_value": 0, "max_value": 50}),
    ]
)
results_dq.append(("terminals", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── berths ──")
df = spark.table(f"{bronze_portops}.berths")

df_silver = (df
    .withColumn("berth_id",    col("berth_id").cast(IntegerType()))
    .withColumn("terminal_id", col("terminal_id").cast(IntegerType()))
    .withColumn("length_m",    col("length_m").cast(DoubleType()))
    .withColumn("depth_m",     col("depth_m").cast(DoubleType()))
    .withColumn("berth_name",  trim(col("berth_name")))
    .withColumn("berth_type",  trim(col("berth_type")))
    .filter(col("berth_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_portops}.berths", "berth_id")
print(f"  ✅ silver_portops.berths → {cnt:,} rows")

apply_constraints(f"{silver_portops}.berths", [
    ("berths_id_positive",   "berth_id > 0"),
    ("berths_term_positive", "terminal_id > 0"),
    ("berths_length_pos",    "length_m > 0"),
    ("berths_depth_valid",   "depth_m > 0 AND depth_m <= 50"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_portops}.berths"), "berths", [
        ("expect_column_values_to_not_be_null", {"column": "berth_id"}),
        ("expect_column_values_to_be_unique",   {"column": "berth_id"}),
        ("expect_column_values_to_be_between",  {"column": "length_m", "min_value": 0}),
        ("expect_column_values_to_be_between",  {"column": "depth_m", "min_value": 0, "max_value": 50}),
    ]
)
results_dq.append(("berths", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── voyages ──")
df = spark.table(f"{bronze_navigation}.voyages")

df_silver = (df
    .withColumn("voyage_id",           col("voyage_id").cast(IntegerType()))
    .withColumn("vessel_id",           col("vessel_id").cast(IntegerType()))
    .withColumn("origin_port_id",      col("origin_port_id").cast(IntegerType()))
    .withColumn("destination_port_id", col("destination_port_id").cast(IntegerType()))
    .withColumn("distance_nm",         col("distance_nm").cast(DoubleType()))
    .withColumn("etd",                 to_timestamp(col("etd")))
    .withColumn("atd",                 to_timestamp(col("atd")))
    .withColumn("eta",                 to_timestamp(col("eta")))
    .withColumn("ata",                 to_timestamp(col("ata")))
    .withColumn("voyage_code",         trim(col("voyage_code")))
    .withColumn("voyage_status",       trim(lower(col("voyage_status"))))
    .filter(col("voyage_id").isNotNull())
    .filter(col("vessel_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_navigation}.voyages", "voyage_id")
print(f"  ✅ silver_navigation.voyages → {cnt:,} rows")

apply_constraints(f"{silver_navigation}.voyages", [
    ("voyages_id_positive",     "voyage_id > 0"),
    ("voyages_vessel_positive", "vessel_id > 0"),
    ("voyages_distance_pos",    "distance_nm > 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_navigation}.voyages"), "voyages", [
        ("expect_column_values_to_not_be_null", {"column": "voyage_id"}),
        ("expect_column_values_to_be_unique",   {"column": "voyage_id"}),
        ("expect_column_values_to_not_be_null", {"column": "vessel_id"}),
        ("expect_column_values_to_be_between",  {"column": "distance_nm", "min_value": 0}),
        ("expect_column_values_to_be_in_set",   {"column": "voyage_status", "value_set": ["planned", "in progress", "completed", "cancelled"]}),
    ]
)
results_dq.append(("voyages", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── port_calls ──")
df = spark.table(f"{bronze_navigation}.port_calls")

df_silver = (df
    .withColumn("port_call_id", col("port_call_id").cast(IntegerType()))
    .withColumn("voyage_id",    col("voyage_id").cast(IntegerType()))
    .withColumn("port_id",      col("port_id").cast(IntegerType()))
    .withColumn("berth_id",     col("berth_id").cast(IntegerType()))
    .withColumn("eta",          to_timestamp(col("eta")))
    .withColumn("ata",          to_timestamp(col("ata")))
    .withColumn("etd",          to_timestamp(col("etd")))
    .withColumn("atd",          to_timestamp(col("atd")))
    .withColumn("call_purpose", trim(col("call_purpose")))
    .filter(col("port_call_id").isNotNull())
    .filter(col("port_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_navigation}.port_calls", "port_call_id")
print(f"  ✅ silver_navigation.port_calls → {cnt:,} rows")

apply_constraints(f"{silver_navigation}.port_calls", [
    ("pc_id_positive",   "port_call_id > 0"),
    ("pc_port_positive", "port_id > 0"),
    ("pc_voy_positive",  "voyage_id > 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_navigation}.port_calls"), "port_calls", [
        ("expect_column_values_to_not_be_null", {"column": "port_call_id"}),
        ("expect_column_values_to_be_unique",   {"column": "port_call_id"}),
        ("expect_column_values_to_not_be_null", {"column": "port_id"}),
        ("expect_column_values_to_not_be_null", {"column": "voyage_id"}),
        ("expect_column_values_to_not_be_null", {"column": "eta"}),
    ]
)
results_dq.append(("port_calls", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── cargo_types ──")
df = spark.table(f"{bronze_cargo}.cargo_types")

df_silver = (df
    .withColumn("cargo_type_id", col("cargo_type_id").cast(IntegerType()))
    .withColumn("type_code",     trim(upper(col("type_code"))))
    .withColumn("type_name",     trim(col("type_name")))
    .withColumn("category",      trim(col("category")))
    .withColumn("hazmat_class",  trim(col("hazmat_class")))
    .filter(col("cargo_type_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_cargo}.cargo_types", "cargo_type_id")
print(f"  ✅ silver_cargo.cargo_types → {cnt:,} rows")

apply_constraints(f"{silver_cargo}.cargo_types", [
    ("ct_id_positive",   "cargo_type_id > 0"),
    ("ct_name_notnull",  "type_name IS NOT NULL"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_cargo}.cargo_types"), "cargo_types", [
        ("expect_column_values_to_not_be_null", {"column": "cargo_type_id"}),
        ("expect_column_values_to_be_unique",   {"column": "cargo_type_id"}),
        ("expect_column_values_to_not_be_null", {"column": "type_name"}),
        ("expect_column_values_to_not_be_null", {"column": "type_code"}),
    ]
)
results_dq.append(("cargo_types", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── cargo_orders ──")
df = spark.table(f"{bronze_cargo}.cargo_orders")

df_silver = (df
    .withColumn("order_id",      col("order_id").cast(IntegerType()))
    .withColumn("cargo_type_id", col("cargo_type_id").cast(IntegerType()))
    .withColumn("voyage_id",     col("voyage_id").cast(IntegerType()))
    .withColumn("tonnage",       col("tonnage").cast(DoubleType()))
    .withColumn("volume_m3",     col("volume_m3").cast(DoubleType()))
    .withColumn("freight_rate",  col("freight_rate").cast(DoubleType()))
    .withColumn("order_code",    trim(col("order_code")))
    .withColumn("client_name",   trim(col("client_name")))
    .withColumn("order_status",  trim(col("order_status")))
    .withColumn("created_at",    to_timestamp(col("created_at")))
    .filter(col("order_id").isNotNull())
    .filter(col("tonnage") > 0)
)

df_silver, cnt = write_silver(df_silver, f"{silver_cargo}.cargo_orders", "order_id")
print(f"  ✅ silver_cargo.cargo_orders → {cnt:,} rows")

apply_constraints(f"{silver_cargo}.cargo_orders", [
    ("co_id_positive",      "order_id > 0"),
    ("co_tonnage_positive", "tonnage > 0"),
    ("co_rate_positive",    "freight_rate >= 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_cargo}.cargo_orders"), "cargo_orders", [
        ("expect_column_values_to_not_be_null", {"column": "order_id"}),
        ("expect_column_values_to_be_unique",   {"column": "order_id"}),
        ("expect_column_values_to_be_between",  {"column": "tonnage", "min_value": 0}),
        ("expect_column_values_to_be_between",  {"column": "freight_rate", "min_value": 0}),
        ("expect_column_values_to_not_be_null", {"column": "cargo_type_id"}),
    ]
)
results_dq.append(("cargo_orders", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── cargo_manifests ──")
df = spark.table(f"{bronze_cargo}.cargo_manifests")

df_silver = (df
    .withColumn("manifest_id",       col("manifest_id").cast(IntegerType()))
    .withColumn("order_id",          col("order_id").cast(IntegerType()))
    .withColumn("load_port_id",      col("load_port_id").cast(IntegerType()))
    .withColumn("discharge_port_id", col("discharge_port_id").cast(IntegerType()))
    .withColumn("actual_tonnage",    col("actual_tonnage").cast(DoubleType()))
    .withColumn("declared_value",    col("declared_value").cast(DoubleType()))
    .withColumn("manifest_code",     trim(col("manifest_code")))
    .withColumn("customs_status",    trim(col("customs_status")))
    .filter(col("manifest_id").isNotNull())
    .filter(col("actual_tonnage") > 0)
)

df_silver, cnt = write_silver(df_silver, f"{silver_cargo}.cargo_manifests", "manifest_id")
print(f"  ✅ silver_cargo.cargo_manifests → {cnt:,} rows")

apply_constraints(f"{silver_cargo}.cargo_manifests", [
    ("cm_id_positive",    "manifest_id > 0"),
    ("cm_tonnage_pos",    "actual_tonnage > 0"),
    ("cm_order_positive", "order_id > 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_cargo}.cargo_manifests"), "cargo_manifests", [
        ("expect_column_values_to_not_be_null", {"column": "manifest_id"}),
        ("expect_column_values_to_be_unique",   {"column": "manifest_id"}),
        ("expect_column_values_to_be_between",  {"column": "actual_tonnage", "min_value": 0}),
        ("expect_column_values_to_not_be_null", {"column": "order_id"}),
    ]
)
results_dq.append(("cargo_manifests", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── cargo_manifests ──")
df = spark.table(f"{bronze_cargo}.cargo_manifests")

df_silver = (df
    .withColumn("manifest_id",       col("manifest_id").cast(IntegerType()))
    .withColumn("order_id",          col("order_id").cast(IntegerType()))
    .withColumn("load_port_id",      col("load_port_id").cast(IntegerType()))
    .withColumn("discharge_port_id", col("discharge_port_id").cast(IntegerType()))
    .withColumn("actual_tonnage",    col("actual_tonnage").cast(DoubleType()))
    .withColumn("declared_value",    col("declared_value").cast(DoubleType()))
    .withColumn("manifest_code",     trim(col("manifest_code")))
    .withColumn("customs_status",    trim(col("customs_status")))
    .filter(col("manifest_id").isNotNull())
    .filter(col("actual_tonnage") > 0)
)

df_silver, cnt = write_silver(df_silver, f"{silver_cargo}.cargo_manifests", "manifest_id")
print(f"  ✅ silver_cargo.cargo_manifests → {cnt:,} rows")

apply_constraints(f"{silver_cargo}.cargo_manifests", [
    ("cm_id_positive",    "manifest_id > 0"),
    ("cm_tonnage_pos",    "actual_tonnage > 0"),
    ("cm_order_positive", "order_id > 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_cargo}.cargo_manifests"), "cargo_manifests", [
        ("expect_column_values_to_not_be_null", {"column": "manifest_id"}),
        ("expect_column_values_to_be_unique",   {"column": "manifest_id"}),
        ("expect_column_values_to_be_between",  {"column": "actual_tonnage", "min_value": 0}),
        ("expect_column_values_to_not_be_null", {"column": "order_id"}),
    ]
)
results_dq.append(("cargo_manifests", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── fuel_grades ──")
df = spark.table(f"{bronze_fuelops}.fuel_grades")

df_silver = (df
    .withColumn("fuel_grade_id",  col("fuel_grade_id").cast(IntegerType()))
    .withColumn("sulfur_content", col("sulfur_content").cast(DoubleType()))
    .withColumn("grade_code",     trim(upper(col("grade_code"))))
    .withColumn("grade_name",     trim(col("grade_name")))
    .withColumn("imo_compliant",  col("imo_compliant").cast("boolean"))
    .filter(col("fuel_grade_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_fuelops}.fuel_grades", "fuel_grade_id")
print(f"  ✅ silver_fuelops.fuel_grades → {cnt:,} rows")

apply_constraints(f"{silver_fuelops}.fuel_grades", [
    ("fg_id_positive",   "fuel_grade_id > 0"),
    ("fg_sulfur_valid",  "sulfur_content >= 0 AND sulfur_content <= 5"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_fuelops}.fuel_grades"), "fuel_grades", [
        ("expect_column_values_to_not_be_null", {"column": "fuel_grade_id"}),
        ("expect_column_values_to_be_unique",   {"column": "fuel_grade_id"}),
        ("expect_column_values_to_be_between",  {"column": "sulfur_content", "min_value": 0, "max_value": 5}),
        ("expect_column_values_to_not_be_null", {"column": "grade_name"}),
    ]
)
results_dq.append(("fuel_grades", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── bunkering_events ──")
df = spark.table(f"{bronze_fuelops}.bunkering_events")

df_silver = (df
    .withColumn("bunker_id",      col("bunker_id").cast(IntegerType()))
    .withColumn("vessel_id",      col("vessel_id").cast(IntegerType()))
    .withColumn("port_id",        col("port_id").cast(IntegerType()))
    .withColumn("fuel_grade_id",  col("fuel_grade_id").cast(IntegerType()))
    .withColumn("quantity_mt",    col("quantity_mt").cast(DoubleType()))
    .withColumn("unit_price_usd", col("unit_price_usd").cast(DoubleType()))
    .withColumn("total_cost_usd", col("total_cost_usd").cast(DoubleType()))
    .withColumn("bunker_date",    to_date(col("bunker_date")))
    .withColumn("supplier_name",  trim(col("supplier_name")))
    .filter(col("bunker_id").isNotNull())
    .filter(col("quantity_mt") > 0)
)

df_silver, cnt = write_silver(df_silver, f"{silver_fuelops}.bunkering_events", "bunker_id")
print(f"  ✅ silver_fuelops.bunkering_events → {cnt:,} rows")

apply_constraints(f"{silver_fuelops}.bunkering_events", [
    ("be_id_positive",    "bunker_id > 0"),
    ("be_qty_positive",   "quantity_mt > 0"),
    ("be_price_positive", "unit_price_usd > 0"),
    ("be_cost_positive",  "total_cost_usd > 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_fuelops}.bunkering_events"), "bunkering_events", [
        ("expect_column_values_to_not_be_null", {"column": "bunker_id"}),
        ("expect_column_values_to_be_unique",   {"column": "bunker_id"}),
        ("expect_column_values_to_be_between",  {"column": "quantity_mt", "min_value": 0}),
        ("expect_column_values_to_be_between",  {"column": "unit_price_usd", "min_value": 0}),
        ("expect_column_values_to_not_be_null", {"column": "bunker_date"}),
    ]
)
results_dq.append(("bunkering_events", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── seafarers ──")
df = spark.table(f"{bronze_crewing}.seafarers")

df_silver = (df
    .withColumn("seafarer_id",   col("seafarer_id").cast(IntegerType()))
    .withColumn("date_of_birth", to_date(col("date_of_birth")))
    .withColumn("full_name",     trim(col("full_name")))
    .withColumn("nationality",   trim(upper(col("nationality"))))
    .withColumn("rank_title",    trim(col("rank_title")))
    .withColumn("seafarer_code", trim(col("seafarer_code")))
    .withColumn("stcw_number",   trim(col("stcw_number")))
    .filter(col("seafarer_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_crewing}.seafarers", "seafarer_id")
print(f"  ✅ silver_crewing.seafarers → {cnt:,} rows")

apply_constraints(f"{silver_crewing}.seafarers", [
    ("sf_id_positive",    "seafarer_id > 0"),
    ("sf_name_notnull",   "full_name IS NOT NULL"),
    ("sf_rank_notnull",   "rank_title IS NOT NULL"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_crewing}.seafarers"), "seafarers", [
        ("expect_column_values_to_not_be_null", {"column": "seafarer_id"}),
        ("expect_column_values_to_be_unique",   {"column": "seafarer_id"}),
        ("expect_column_values_to_not_be_null", {"column": "full_name"}),
        ("expect_column_values_to_not_be_null", {"column": "rank_title"}),
        ("expect_column_values_to_not_be_null", {"column": "nationality"}),
    ]
)
results_dq.append(("seafarers", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── crew_assignments ──")
df = spark.table(f"{bronze_crewing}.crew_assignments")

df_silver = (df
    .withColumn("assignment_id", col("assignment_id").cast(IntegerType()))
    .withColumn("seafarer_id",   col("seafarer_id").cast(IntegerType()))
    .withColumn("vessel_id",     col("vessel_id").cast(IntegerType()))
    .withColumn("voyage_id",     col("voyage_id").cast(IntegerType()))
    .withColumn("embark_date",   to_date(col("embark_date")))
    .withColumn("disembark_date",to_date(col("disembark_date")))
    .withColumn("role_onboard",  trim(col("role_onboard")))
    .filter(col("assignment_id").isNotNull())
    .filter(col("seafarer_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_crewing}.crew_assignments", "assignment_id")
print(f"  ✅ silver_crewing.crew_assignments → {cnt:,} rows")

apply_constraints(f"{silver_crewing}.crew_assignments", [
    ("ca_id_positive",    "assignment_id > 0"),
    ("ca_seafarer_pos",   "seafarer_id > 0"),
    ("ca_vessel_pos",     "vessel_id > 0"),
    ("ca_role_notnull",   "role_onboard IS NOT NULL"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_crewing}.crew_assignments"), "crew_assignments", [
        ("expect_column_values_to_not_be_null", {"column": "assignment_id"}),
        ("expect_column_values_to_be_unique",   {"column": "assignment_id"}),
        ("expect_column_values_to_not_be_null", {"column": "seafarer_id"}),
        ("expect_column_values_to_not_be_null", {"column": "embark_date"}),
        ("expect_column_values_to_not_be_null", {"column": "role_onboard"}),
    ]
)
results_dq.append(("crew_assignments", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── clients ──")
df = spark.table(f"{bronze_commercial}.clients")

df_silver = (df
    .withColumn("client_id",      col("client_id").cast(IntegerType()))
    .withColumn("credit_limit",   col("credit_limit").cast(DoubleType()))
    .withColumn("company_name",   trim(col("company_name")))
    .withColumn("client_code",    trim(upper(col("client_code"))))
    .withColumn("country",        trim(upper(col("country"))))
    .withColumn("segment",        trim(col("segment")))
    .withColumn("payment_terms",  trim(col("payment_terms")))
    .filter(col("client_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_commercial}.clients", "client_id")
print(f"  ✅ silver_commercial.clients → {cnt:,} rows")

apply_constraints(f"{silver_commercial}.clients", [
    ("cl_id_positive",   "client_id > 0"),
    ("cl_name_notnull",  "company_name IS NOT NULL"),
    ("cl_credit_pos",    "credit_limit >= 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_commercial}.clients"), "clients", [
        ("expect_column_values_to_not_be_null", {"column": "client_id"}),
        ("expect_column_values_to_be_unique",   {"column": "client_id"}),
        ("expect_column_values_to_not_be_null", {"column": "company_name"}),
        ("expect_column_values_to_be_between",  {"column": "credit_limit", "min_value": 0}),
        ("expect_column_values_to_not_be_null", {"column": "country"}),
    ]
)
results_dq.append(("clients", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

print("\n── contracts ──")
df = spark.table(f"{bronze_commercial}.contracts")

df_silver = (df
    .withColumn("contract_id",     col("contract_id").cast(IntegerType()))
    .withColumn("client_id",       col("client_id").cast(IntegerType()))
    .withColumn("vessel_id",       col("vessel_id").cast(IntegerType()))
    .withColumn("base_rate",       col("base_rate").cast(DoubleType()))
    .withColumn("start_date",      to_date(col("start_date")))
    .withColumn("end_date",        to_date(col("end_date")))
    .withColumn("contract_code",   trim(col("contract_code")))
    .withColumn("contract_type",   trim(col("contract_type")))
    .withColumn("currency",        trim(upper(col("currency"))))
    .withColumn("contract_status", trim(col("contract_status")))
    .filter(col("contract_id").isNotNull())
)

df_silver, cnt = write_silver(df_silver, f"{silver_commercial}.contracts", "contract_id")
print(f"  ✅ silver_commercial.contracts → {cnt:,} rows")

apply_constraints(f"{silver_commercial}.contracts", [
    ("con_id_positive",  "contract_id > 0"),
    ("con_rate_pos",     "base_rate > 0"),
    ("con_client_pos",   "client_id > 0"),
    ("con_vessel_pos",   "vessel_id > 0"),
])

passed, total, failed = run_ge_validation(
    spark.table(f"{silver_commercial}.contracts"), "contracts", [
        ("expect_column_values_to_not_be_null", {"column": "contract_id"}),
        ("expect_column_values_to_be_unique",   {"column": "contract_id"}),
        ("expect_column_values_to_be_between",  {"column": "base_rate", "min_value": 0}),
        ("expect_column_values_to_not_be_null", {"column": "start_date"}),
        ("expect_column_values_to_not_be_null", {"column": "end_date"}),
        ("expect_column_values_to_not_be_null", {"column": "client_id"}),
    ]
)
results_dq.append(("contracts", cnt, passed, total, failed))
print(f"  📊 GE : {passed}/{total} checks passed" + (f" | ⚠️ {failed}" if failed else ""))

# COMMAND ----------

end_time     = datetime.now()
duration     = (end_time - start_time).seconds
total_rows   = sum(r[1] for r in results_dq)
total_checks = sum(r[3] for r in results_dq)
total_passed = sum(r[2] for r in results_dq)
total_failed = total_checks - total_passed

print("\n" + "=" * 60)
print("  silver_erp — Data Quality Summary")
print("=" * 60)
print(f"  {'Table':<25} {'Rows':>8}  {'GE':>10}  Status")
print("-" * 60)
for tbl, rows, passed, total, failed in results_dq:
    status = "✅" if not failed else "⚠️"
    print(f"  {tbl:<25} {rows:>8,}  {passed}/{total} checks  {status}")
print("-" * 60)
print(f"  {'TOTAL':<25} {total_rows:>8,}  {total_passed}/{total_checks} checks")
print(f"  Duration  : {duration}s")
print(f"  Ended     : {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

if total_failed > 0:
    print("\n  ⚠️  Checks échoués :")
    for tbl, rows, passed, total, failed in results_dq:
        if failed:
            print(f"    → {tbl} : {failed}")