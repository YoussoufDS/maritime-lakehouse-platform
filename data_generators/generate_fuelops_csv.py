"""
Maritime Lakehouse Platform
Generateur fichiers CSV - Domaine FUELOPS
Simule un Fuel Management System (Bunkerworld/Q88)
Output : landing/files/fuelops/
"""

import csv
import os
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)

OUTPUT_DIR = "output_files/landing/files/fuelops"
os.makedirs(f"{OUTPUT_DIR}/consumption_logs", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/bunkering_events", exist_ok=True)

VESSEL_IDS  = list(range(1, 151))
PORT_NAMES  = ["Montreal","Rotterdam","Singapore","Shanghai","Houston",
               "Hamburg","Dubai","Busan","Santos","Melbourne"]
FUEL_GRADES = ["HFO","VLSFO","MGO","LNG","LSMGO"]
SUPPLIERS   = ["World Fuel Services","Peninsula","Bomin","Integr8","Bunker One"]

def generate_consumption_logs():
    """
    Consommation journaliere de carburant par navire
    1 fichier par mois sur 36 mois (2021-2023)
    """
    print("Generating fuel consumption logs...")
    start = datetime(2021, 1, 1)
    total = 0

    for month_offset in range(36):
        current_month = start + timedelta(days=month_offset * 30)
        year  = current_month.year
        month = current_month.month
        days_in_month = 30

        folder = f"{OUTPUT_DIR}/consumption_logs/year={year}/month={month:02d}"
        os.makedirs(folder, exist_ok=True)
        filename = f"{folder}/consumption_{year}{month:02d}.csv"

        rows = []
        for vessel_id in VESSEL_IDS:
            for day in range(1, days_in_month + 1):
                log_date = datetime(year, month, min(day, 28))
                speed_knots   = round(random.uniform(8, 18), 1)
                consumption_mt = round(random.uniform(15, 85), 2)
                distance_nm   = round(speed_knots * 24, 1)
                eeoi = round(consumption_mt * 3.114 / max(distance_nm * 0.001, 0.01), 4)
                rows.append({
                    "log_date"        : log_date.strftime("%Y-%m-%d"),
                    "vessel_id"       : vessel_id,
                    "fuel_grade"      : random.choice(FUEL_GRADES),
                    "consumption_mt"  : consumption_mt,
                    "speed_knots"     : speed_knots,
                    "distance_nm"     : distance_nm,
                    "running_hours"   : 24,
                    "eeoi"            : eeoi,
                    "load_factor"     : round(random.uniform(0.4, 1.0), 2),
                    "sea_condition"   : random.choice(["Calm","Moderate","Rough"]),
                    "source_system"   : "FMS_MARITIME",
                    "ingestion_date"  : datetime.now().strftime("%Y-%m-%d")
                })
                total += 1

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        if month_offset % 6 == 0:
            print(f"  {year}-{month:02d} generated...")

    print(f"  OK - {total:,} consumption log rows")
    return total

def generate_bunkering_events():
    """
    Evenements de soutage (bunkering) 
    1 fichier par trimestre sur 3 ans
    """
    print("Generating bunkering events...")
    start = datetime(2021, 1, 1)
    total = 0

    for quarter in range(12):
        q_start = start + timedelta(days=quarter * 90)
        year    = q_start.year
        q_num   = (q_start.month - 1) // 3 + 1

        folder   = f"{OUTPUT_DIR}/bunkering_events/year={year}"
        os.makedirs(folder, exist_ok=True)
        filename = f"{folder}/bunkering_{year}_Q{q_num}.csv"

        rows = []
        n_events = random.randint(800, 1200)
        for _ in range(n_events):
            event_date = q_start + timedelta(days=random.randint(0, 89))
            qty        = round(random.uniform(50, 3000), 2)
            price      = round(random.uniform(350, 850), 2)
            rows.append({
                "bunker_date"    : event_date.strftime("%Y-%m-%d"),
                "vessel_id"      : random.choice(VESSEL_IDS),
                "port_name"      : random.choice(PORT_NAMES),
                "fuel_grade"     : random.choice(FUEL_GRADES),
                "quantity_mt"    : qty,
                "unit_price_usd" : price,
                "total_cost_usd" : round(qty * price, 2),
                "supplier"       : random.choice(SUPPLIERS),
                "rob_before_mt"  : round(random.uniform(100, 2000), 2),
                "rob_after_mt"   : round(random.uniform(500, 3000), 2),
                "source_system"  : "BUNKERWORLD",
                "ingestion_date" : datetime.now().strftime("%Y-%m-%d")
            })
            total += 1

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(f"  OK - {total:,} bunkering event rows")
    return total

if __name__ == "__main__":
    print("=" * 55)
    print("  Maritime Lakehouse - FUELOPS CSV Generator")
    print("  Output: output_files/landing/files/fuelops/")
    print("=" * 55)
    r1 = generate_consumption_logs()
    r2 = generate_bunkering_events()
    print("\n" + "=" * 55)
    print("  Generation complete!")
    print(f"  - Consumption logs : {r1:,} rows")
    print(f"  - Bunkering events : {r2:,} rows")
    print("  Upload folder: output_files/landing/files/fuelops/")
    print("=" * 55)
