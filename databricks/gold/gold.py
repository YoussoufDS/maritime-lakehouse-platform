# Databricks notebook source
# MAGIC %run /Workspace/Users/raissa.tchotchoua-tonou@hec.ca/Config

# COMMAND ----------

# CELLULE 2 — Imports
from pyspark.sql.functions import (
    current_timestamp, lit, col, trim, upper, lower,
    to_date, to_timestamp, when, coalesce, round,
    year, month, quarter, dayofweek, dayofmonth,
    date_format, datediff, expr, sum as spark_sum,
    avg, min as spark_min, max as spark_max, count,
    monotonically_increasing_id, sequence, explode
)
from pyspark.sql.types import (
    IntegerType, DoubleType, StringType,
    DateType, BooleanType
)
from datetime import datetime, date

start_time  = datetime.now()
results_gold = []

print(f"Start : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# COMMAND ----------

# CELLULE 3 — Fonction write_gold
def write_gold(df, table_name):
    target = f"{gold}.{table_name}"
    df = (df
        .withColumn("_gold_timestamp", current_timestamp())
        .withColumn("_gold_pipeline",  lit("gold"))
    )
    (df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(target)
    )
    cnt = spark.table(target).count()
    results_gold.append((table_name, cnt))
    print(f"  ✅ gold.{table_name:<25} → {cnt:,} rows")
    return cnt

# COMMAND ----------

# CELLULE 4 — dim_vessel
print("\n── dim_vessel ──")

vessels = spark.table(f"{silver_fleet}.vessels")
classes = spark.table(f"{silver_fleet}.vessel_classes")

dim_vessel = (vessels
    .join(classes, on="class_id", how="left")
    .select(
        col("vessel_id"),
        col("imo_number"),
        col("vessel_name"),
        col("class_id"),
        col("class_name"),
        col("vessel_type"),
        col("flag_country"),
        col("build_year"),
        col("deadweight_tons"),
        col("teu_capacity"),
        col("gross_tonnage"),
        col("max_dwt"),
        col("max_teu"),
        col("avg_speed_knots"),
        col("status"),
        col("owner_company"),
    )
)

write_gold(dim_vessel, "dim_vessel")

# COMMAND ----------

# CELLULE 5 — dim_port
print("\n── dim_port ──")

ports     = spark.table(f"{silver_portops}.ports")
terminals = spark.table(f"{silver_portops}.terminals")

# Agréger les terminaux par port
terminals_agg = (terminals
    .groupBy("port_id")
    .agg(
        count("terminal_id").alias("terminal_count"),
        spark_sum("berth_count").alias("total_berths"),
        spark_max("max_depth_m").alias("max_depth_m"),
    )
)

dim_port = (ports
    .join(terminals_agg, on="port_id", how="left")
    .select(
        col("port_id"),
        col("port_code"),
        col("port_name"),
        col("country"),
        col("region"),
        col("latitude"),
        col("longitude"),
        col("port_type"),
        col("max_vessel_dwt"),
        col("timezone"),
        coalesce(col("terminal_count"), lit(0)).alias("terminal_count"),
        coalesce(col("total_berths"),   lit(0)).alias("total_berths"),
        coalesce(col("max_depth_m"),    lit(0.0)).alias("max_depth_m"),
    )
)

write_gold(dim_port, "dim_port")

# COMMAND ----------

# CELLULE 6 — dim_date
print("\n── dim_date ──")

# Générer calendrier 2020-2026
date_range = spark.sql("""
    SELECT explode(sequence(
        to_date('2020-01-01'),
        to_date('2026-12-31'),
        interval 1 day
    )) AS date
""")

dim_date = (date_range
    .withColumn("date_id",       date_format(col("date"), "yyyyMMdd").cast(IntegerType()))
    .withColumn("year",          year(col("date")))
    .withColumn("quarter",       quarter(col("date")))
    .withColumn("month",         month(col("date")))
    .withColumn("month_name",    date_format(col("date"), "MMMM"))
    .withColumn("week",          expr("weekofyear(date)"))
    .withColumn("day_of_month",  dayofmonth(col("date")))
    .withColumn("day_of_week",   dayofweek(col("date")))
    .withColumn("day_name",      date_format(col("date"), "EEEE"))
    .withColumn("is_weekend",    (dayofweek(col("date")).isin(1, 7)).cast(BooleanType()))
    .withColumn("quarter_name",  expr("concat('Q', quarter)"))
    .withColumn("year_month",    date_format(col("date"), "yyyy-MM"))
    .withColumn("year_quarter",  expr("concat(year, '-Q', quarter)"))
)

write_gold(dim_date, "dim_date")

# COMMAND ----------

# CELLULE 7 — fact_voyage
print("\n── fact_voyage ──")

voyages  = spark.table(f"{silver_navigation}.voyages")
vessels  = spark.table(f"{silver_fleet}.vessels").select(
    "vessel_id", "class_id", "deadweight_tons", "gross_tonnage"
)

fact_voyage = (voyages
    .join(vessels, on="vessel_id", how="left")
    .withColumn("departure_date_id",
        date_format(col("atd"), "yyyyMMdd").cast(IntegerType())
    )
    .withColumn("arrival_date_id",
        date_format(col("ata"), "yyyyMMdd").cast(IntegerType())
    )
    .withColumn("voyage_duration_days",
        round(datediff(col("ata"), col("atd")).cast(DoubleType()), 2)
    )
    .withColumn("avg_speed_actual",
        round(
            when(
                (col("voyage_duration_days") > 0) & (col("distance_nm") > 0),
                col("distance_nm") / (col("voyage_duration_days") * 24)
            ), 2
        )
    )
    .withColumn("is_completed",
        (col("voyage_status") == "completed").cast(BooleanType())
    )
    .select(
        col("voyage_id"),
        col("voyage_code"),
        col("vessel_id"),
        col("class_id"),
        col("origin_port_id"),
        col("destination_port_id"),
        col("departure_date_id"),
        col("arrival_date_id"),
        col("distance_nm"),
        col("voyage_duration_days"),
        col("avg_speed_actual"),
        col("voyage_status"),
        col("is_completed"),
        col("deadweight_tons"),
        col("gross_tonnage"),
    )
)

write_gold(fact_voyage, "fact_voyage")

# COMMAND ----------

# CELLULE 8 — fact_port_call
print("\n── fact_port_call ──")

port_calls = spark.table(f"{silver_navigation}.port_calls")
voyages_fk = spark.table(f"{silver_navigation}.voyages").select(
    "voyage_id", "vessel_id"
)

fact_port_call = (port_calls
    .join(voyages_fk, on="voyage_id", how="left")
    .withColumn("arrival_date_id",
        date_format(col("ata"), "yyyyMMdd").cast(IntegerType())
    )
    .withColumn("departure_date_id",
        date_format(col("atd"), "yyyyMMdd").cast(IntegerType())
    )
    .withColumn("port_stay_hours",
        round(
            when(
                col("ata").isNotNull() & col("atd").isNotNull(),
                (col("atd").cast("long") - col("ata").cast("long")) / 3600
            ), 2
        )
    )
    .withColumn("port_stay_days",
        round(col("port_stay_hours") / 24, 2)
    )
    .select(
        col("port_call_id"),
        col("voyage_id"),
        col("vessel_id"),
        col("port_id"),
        col("berth_id"),
        col("arrival_date_id"),
        col("departure_date_id"),
        col("ata"),
        col("atd"),
        col("port_stay_hours"),
        col("port_stay_days"),
        col("call_purpose"),
    )
)

write_gold(fact_port_call, "fact_port_call")

# COMMAND ----------

# CELLULE 9 — fact_cargo
print("\n── fact_cargo ──")

cargo_orders    = spark.table(f"{silver_cargo}.cargo_orders")
cargo_manifests = spark.table(f"{silver_cargo}.cargo_manifests")
cargo_types     = spark.table(f"{silver_cargo}.cargo_types").select(
    "cargo_type_id", "type_name", "category", "hazmat_class"
)
voyages_fk = spark.table(f"{silver_navigation}.voyages").select(
    "voyage_id", "vessel_id", "origin_port_id", "destination_port_id"
)

# Agréger manifests par order
manifests_agg = (cargo_manifests
    .groupBy("order_id")
    .agg(
        spark_sum("actual_tonnage").alias("actual_tonnage"),
        spark_sum("declared_value").alias("declared_value"),
        count("manifest_id").alias("manifest_count"),
    )
)

fact_cargo = (cargo_orders
    .join(cargo_types,     on="cargo_type_id", how="left")
    .join(voyages_fk,      on="voyage_id",     how="left")
    .join(manifests_agg,   on="order_id",      how="left")
    .withColumn("order_date_id",
        date_format(col("created_at"), "yyyyMMdd").cast(IntegerType())
    )
    .withColumn("revenue_usd",
        round(col("tonnage") * col("freight_rate"), 2)
    )
    .withColumn("tonnage_variance",
        round(col("actual_tonnage") - col("tonnage"), 2)
    )
    .select(
        col("order_id"),
        col("order_code"),
        col("voyage_id"),
        col("vessel_id"),
        col("origin_port_id"),
        col("destination_port_id"),
        col("cargo_type_id"),
        col("type_name").alias("cargo_type_name"),
        col("category").alias("cargo_category"),
        col("hazmat_class"),
        col("order_date_id"),
        col("client_name"),
        col("tonnage"),
        col("volume_m3"),
        col("freight_rate"),
        col("revenue_usd"),
        coalesce(col("actual_tonnage"),   col("tonnage")).alias("actual_tonnage"),
        coalesce(col("declared_value"),   lit(0.0)).alias("declared_value"),
        coalesce(col("manifest_count"),   lit(0)).alias("manifest_count"),
        coalesce(col("tonnage_variance"), lit(0.0)).alias("tonnage_variance"),
        col("order_status"),
    )
)

write_gold(fact_cargo, "fact_cargo")

# COMMAND ----------

# CELLULE 10 — fact_fuel
print("\n── fact_fuel ──")

bunkering   = spark.table(f"{silver_fuelops}.bunkering_events")
consumption = spark.table(f"{silver_fuelops}.consumption_logs")
fuel_grades = spark.table(f"{silver_fuelops}.fuel_grades").select(
    "fuel_grade_id", "grade_name", "grade_code",
    "sulfur_content", "imo_compliant"
)

# Bunkering avec grade details
fact_bunkering = (bunkering
    .join(fuel_grades, on="fuel_grade_id", how="left")
    .withColumn("bunker_date_id",
        date_format(col("bunker_date"), "yyyyMMdd").cast(IntegerType())
    )
    .select(
        col("bunker_id"),
        col("vessel_id"),
        col("port_id"),
        col("fuel_grade_id"),
        col("grade_name"),
        col("grade_code"),
        col("sulfur_content"),
        col("imo_compliant"),
        col("bunker_date"),
        col("bunker_date_id"),
        col("quantity_mt"),
        col("unit_price_usd"),
        col("total_cost_usd"),
        col("supplier_name"),
        lit("bunkering").alias("record_type"),
    )
)

write_gold(fact_bunkering, "fact_bunkering")

# Consumption avec CII indicator
fact_consumption = (consumption
    .withColumn("log_date_id",
        date_format(col("log_date"), "yyyyMMdd").cast(IntegerType())
    )
    .withColumn("cii_indicator",
        when(col("eeoi") <= 150, "A")
        .when(col("eeoi") <= 200, "B")
        .when(col("eeoi") <= 250, "C")
        .when(col("eeoi") <= 320, "D")
        .otherwise("E")
    )
    .select(
        col("vessel_id"),
        col("log_date"),
        col("log_date_id"),
        col("fuel_grade"),
        col("consumption_mt"),
        col("distance_nm"),
        col("speed_knots"),
        col("running_hours"),
        col("eeoi"),
        col("cii_indicator"),
        col("load_factor"),
        col("efficiency_mt_nm"),
        col("sea_condition"),
    )
)

write_gold(fact_consumption, "fact_consumption")

# COMMAND ----------

# CELLULE 11 — fact_crew
print("\n── fact_crew ──")

assignments = spark.table(f"{silver_crewing}.crew_assignments")
seafarers   = spark.table(f"{silver_crewing}.seafarers").select(
    "seafarer_id", "full_name", "nationality",
    "rank_title", "seafarer_code"
)
voyages_fk  = spark.table(f"{silver_navigation}.voyages").select(
    "voyage_id", "origin_port_id", "destination_port_id",
    "atd", "ata"
)

fact_crew = (assignments
    .join(seafarers,  on="seafarer_id", how="left")
    .join(voyages_fk, on="voyage_id",   how="left")
    .withColumn("embark_date_id",
        date_format(col("embark_date"), "yyyyMMdd").cast(IntegerType())
    )
    .withColumn("disembark_date_id",
        date_format(col("disembark_date"), "yyyyMMdd").cast(IntegerType())
    )
    .withColumn("assignment_days",
        datediff(col("disembark_date"), col("embark_date"))
    )
    .select(
        col("assignment_id"),
        col("seafarer_id"),
        col("seafarer_code"),
        col("full_name").alias("seafarer_name"),
        col("nationality"),
        col("rank_title"),
        col("vessel_id"),
        col("voyage_id"),
        col("origin_port_id"),
        col("destination_port_id"),
        col("embark_date"),
        col("embark_date_id"),
        col("disembark_date"),
        col("disembark_date_id"),
        col("assignment_days"),
        col("role_onboard"),
    )
)

write_gold(fact_crew, "fact_crew")

# COMMAND ----------

# CELLULE 12 — Résumé Gold
end_time = datetime.now()
duration = (end_time - start_time).seconds

print("\n" + "=" * 60)
print("  gold — Summary")
print("=" * 60)
print(f"  {'Table':<30} {'Rows':>10}")
print("-" * 60)
for tbl, cnt in results_gold:
    print(f"  {tbl:<30} {cnt:>10,}")
print("-" * 60)
total = sum(r[1] for r in results_gold)
print(f"  {'TOTAL':<30} {total:>10,}")
print(f"  Duration  : {duration}s")
print(f"  Ended     : {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)