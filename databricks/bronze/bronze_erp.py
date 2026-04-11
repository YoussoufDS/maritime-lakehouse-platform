# Databricks notebook source
# MAGIC %run /Users/raissa.tchotchoua-tonou@hec.ca/Config

# COMMAND ----------

# DBTITLE 1,Imports + Start
# CELLULE 1b — Imports
# ─────────────────────────────
from pyspark.sql.functions import current_timestamp, lit
from datetime import datetime

start_time = datetime.now()
print(f"Start : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 55)

# COMMAND ----------

# CELLULE 2 — Définition des tables
# ───────────────────────────────────
tables = [
    # (table_name,          domain_folder,  target_schema,      domain)
    ("vessels",             "fleet",        bronze_fleet,        "fleet"),
    ("vessel_classes",      "fleet",        bronze_fleet,        "fleet"),
    ("voyages",             "navigation",   bronze_navigation,   "navigation"),
    ("ports",               "portops",      bronze_portops,      "portops"),
    ("terminals",           "portops",      bronze_portops,      "portops"),
    ("berths",              "portops",      bronze_portops,      "portops"),
    ("port_calls",          "navigation",   bronze_navigation,   "navigation"),
    ("cargo_types",         "cargo",        bronze_cargo,        "cargo"),
    ("cargo_orders",        "cargo",        bronze_cargo,        "cargo"),
    ("cargo_manifests",     "cargo",        bronze_cargo,        "cargo"),
    ("fuel_grades",         "fuelops",      bronze_fuelops,      "fuelops"),
    ("bunkering_events",    "fuelops",      bronze_fuelops,      "fuelops"),
    ("seafarers",           "crewing",      bronze_crewing,      "crewing"),
    ("crew_assignments",    "crewing",      bronze_crewing,      "crewing"),
    ("clients",             "commercial",   bronze_commercial,   "commercial"),
    ("contracts",           "commercial",   bronze_commercial,   "commercial"),
]


# COMMAND ----------

# CELLULE 3 — Ingestion loop
# ───────────────────────────
results = []

for table_name, domain_folder, target_schema, domain in tables:
    try:
        source_path = f"{landing_erp}/{domain_folder}/{table_name}/"

        df = spark.read.parquet(source_path)

        row_count_source = df.count()

        df = (df
            .withColumn("_ingestion_timestamp", current_timestamp())
            .withColumn("_source", lit(f"sqlserver.MaritimeDB.{table_name}"))
            .withColumn("_pipeline", lit("bronze_erp"))
            .withColumn("_domain", lit(domain))
        )

        (df.write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable(f"{target_schema}.{table_name}")
        )

        row_count_target = spark.table(
            f"{target_schema}.{table_name}"
        ).count()

        status = "✅" if row_count_source == row_count_target else "⚠️"
        results.append((table_name, domain, row_count_target, status))
        print(f"  {status} {table_name:<25} {row_count_target:>8,} rows")

    except Exception as e:
        results.append((table_name, domain, 0, "❌"))
        print(f"  ❌ {table_name:<25} ERROR: {str(e)}")


# COMMAND ----------

# CELLULE 4 — Résumé
# ───────────────────
end_time  = datetime.now()
duration  = (end_time - start_time).seconds
total     = sum(r[2] for r in results)
success   = sum(1 for r in results if r[3] == "✅")
failed    = sum(1 for r in results if r[3] == "❌")

print("\n" + "=" * 55)
print("  bronze_erp — Ingestion Summary")
print("=" * 55)
print(f"  Tables     : {len(tables)}")
print(f"  Success    : {success}")
print(f"  Failed     : {failed}")
print(f"  Total rows : {total:,}")
print(f"  Duration   : {duration}s")
print(f"  Ended      : {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 55)

if failed > 0:
    print("\n  Tables en erreur :")
    for name, domain, cnt, status in results:
        if status == "❌":
            print(f"    → {name}")