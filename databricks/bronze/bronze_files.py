# Databricks notebook source
# MAGIC %run /Workspace/Users/raissa.tchotchoua-tonou@hec.ca/Config

# COMMAND ----------

# CELLULE 2 — Imports
from pyspark.sql.functions import current_timestamp, lit
from datetime import datetime

start_time = datetime.now()
results_files = []

print(f"Start : {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 55)

# COMMAND ----------

# CELLULE 2 — Diagnostic structure files/
print("=== Structure landing/files/ ===")
for domain in dbutils.fs.ls(f"{landing_files}/"):
    print(f"\n  {domain.name}")
    try:
        for sub in dbutils.fs.ls(domain.path):
            print(f"    {sub.name}")
            try:
                for subsub in dbutils.fs.ls(sub.path):
                    print(f"      {subsub.name}")
            except:
                pass
    except:
        pass


# COMMAND ----------

# CELLULE 3 — Ingestion fuelops CSV (partitionné)
print("\n── Ingestion : fuelops (CSV partitionné) ──")

fuelops_base = f"{landing_files}/fuelops/"

# Lire tous les sous-dossiers récursivement
# Spark lit automatiquement la partition year= si présente
results_files = []

try:
    subfolders = dbutils.fs.ls(fuelops_base)
    
    for subfolder in subfolders:
        table_name = subfolder.name.rstrip("/")
        source_path = subfolder.path
        
        print(f"\n  Lecture : {table_name}")
        
        df = (spark.read
            .option("header", "true")
            .option("inferSchema", "true")
            .csv(source_path)
        )
        
        df = (df
            .withColumn("_ingestion_timestamp", current_timestamp())
            .withColumn("_source", lit(f"files.landing.fuelops.{table_name}"))
            .withColumn("_pipeline", lit("bronze_files"))
            .withColumn("_domain", lit("fuelops"))
        )
        
        target_table = f"{bronze_fuelops}.{table_name}_raw"
        
        (df.write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable(target_table)
        )
        
        count = spark.table(target_table).count()
        print(f"  ✅ {table_name}_raw → {count:,} rows")
        results_files.append((table_name, count, "✅"))

except Exception as e:
    print(f"  ❌ fuelops ERROR: {str(e)}")
    results_files.append(("fuelops", 0, "❌"))

# COMMAND ----------

# CELLULE 4 — Ingestion weather JSON
print("\n── Ingestion : weather (JSON) ──")

weather_path = f"{landing_files}/weather/"

try:
    df_weather = (spark.read
        .option("multiLine", "true")
        .json(weather_path)
    )
    
    df_weather = (df_weather
        .withColumn("_ingestion_timestamp", current_timestamp())
        .withColumn("_source", lit("files.landing.weather"))
        .withColumn("_pipeline", lit("bronze_files"))
        .withColumn("_domain", lit("navigation"))
    )
    
    (df_weather.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{bronze_navigation}.weather_raw")
    )
    
    count_weather = spark.table(f"{bronze_navigation}.weather_raw").count()
    print(f"  ✅ weather_raw → {count_weather:,} rows")
    results_files.append(("weather_raw", count_weather, "✅"))

except Exception as e:
    print(f"  ❌ weather ERROR: {str(e)}")
    results_files.append(("weather_raw", 0, "❌"))
    count_weather = 0

# COMMAND ----------

# CELLULE 5 — Résumé
end_time  = datetime.now()
duration  = (end_time - start_time).seconds
total     = sum(r[1] for r in results_files)
success   = sum(1 for r in results_files if r[2] == "✅")
failed    = sum(1 for r in results_files if r[2] == "❌")

print("\n" + "=" * 55)
print("  bronze_files — Ingestion Summary")
print("=" * 55)
for name, count, status in results_files:
    print(f"  {status} {name:<30} {count:>10,} rows")
print("-" * 55)
print(f"  Tables    : {len(results_files)}")
print(f"  Success   : {success}")
print(f"  Failed    : {failed}")
print(f"  Total     : {total:,} rows")
print(f"  Duration  : {duration}s")
print(f"  Ended     : {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 55)