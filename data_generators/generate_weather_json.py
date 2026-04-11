"""
Maritime Lakehouse Platform
Generateur fichiers JSON - WEATHER
Simule un provider meteo (StormGeo/NOAA)
Output : landing/files/weather/
"""

import json
import os
import random
from datetime import datetime, timedelta

random.seed(42)

OUTPUT_DIR = "output_files/landing/files/weather/reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MARITIME_ZONES = [
    {"zone": "North Atlantic",     "lat_range": (40, 65),  "lon_range": (-60, -10)},
    {"zone": "South Atlantic",     "lat_range": (-40, 0),  "lon_range": (-50, 10)},
    {"zone": "North Pacific",      "lat_range": (20, 55),  "lon_range": (120, 180)},
    {"zone": "South Pacific",      "lat_range": (-50, -10),"lon_range": (150, 210)},
    {"zone": "Indian Ocean",       "lat_range": (-30, 20), "lon_range": (40, 100)},
    {"zone": "Mediterranean Sea",  "lat_range": (30, 46),  "lon_range": (-5, 36)},
    {"zone": "North Sea",          "lat_range": (51, 61),  "lon_range": (-4, 10)},
    {"zone": "South China Sea",    "lat_range": (0, 25),   "lon_range": (100, 125)},
    {"zone": "Arabian Sea",        "lat_range": (5, 25),   "lon_range": (55, 78)},
    {"zone": "Gulf of Mexico",     "lat_range": (18, 30),  "lon_range": (-98, -80)},
]

SEA_STATES     = ["Calm","Slight","Moderate","Rough","Very Rough","High","Very High"]
WIND_DIRS      = ["N","NE","E","SE","S","SW","W","NW"]
PRECIP_TYPES   = ["None","Rain","Snow","Fog","Hail"]

def generate_weather_report(report_date, hour):
    """Un rapport meteo = toutes les zones, toutes les 6h"""
    records = []
    for zone in MARITIME_ZONES:
        lat = round(random.uniform(*zone["lat_range"]), 4)
        lon = round(random.uniform(*zone["lon_range"]), 4)
        wind_speed = round(random.uniform(0, 45), 1)
        sea_state_idx = min(int(wind_speed / 7), len(SEA_STATES) - 1)
        records.append({
            "report_timestamp" : f"{report_date}T{hour:02d}:00:00Z",
            "zone_name"        : zone["zone"],
            "latitude"         : lat,
            "longitude"        : lon,
            "wind_speed_knots" : wind_speed,
            "wind_direction"   : random.choice(WIND_DIRS),
            "wave_height_m"    : round(random.uniform(0, 8), 1),
            "sea_state"        : SEA_STATES[sea_state_idx],
            "visibility_nm"    : round(random.uniform(0.5, 20), 1),
            "pressure_hpa"     : round(random.uniform(990, 1030), 1),
            "temp_celsius"     : round(random.uniform(-5, 35), 1),
            "precipitation"    : random.choice(PRECIP_TYPES),
            "current_knots"    : round(random.uniform(0, 3), 1),
            "source"           : "STORMGEO_API",
            "ingestion_date"   : datetime.now().strftime("%Y-%m-%d")
        })
    return records

def generate_all_weather():
    print("Generating weather reports...")
    start = datetime(2021, 1, 1)
    total = 0
    files = 0

    for day_offset in range(365 * 3):
        report_date = start + timedelta(days=day_offset)
        date_str    = report_date.strftime("%Y-%m-%d")
        year        = report_date.year
        month       = report_date.month
        day         = report_date.day

        folder = f"{OUTPUT_DIR}/year={year}/month={month:02d}/day={day:02d}"
        os.makedirs(folder, exist_ok=True)

        for hour in [0, 6, 12, 18]:
            records  = generate_weather_report(date_str, hour)
            filename = f"{folder}/weather_{date_str}_{hour:02d}00.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump({
                    "metadata": {
                        "source"    : "StormGeo Maritime Weather API",
                        "timestamp" : f"{date_str}T{hour:02d}:00:00Z",
                        "version"   : "2.1",
                        "zones"     : len(MARITIME_ZONES)
                    },
                    "records": records
                }, f, indent=2)
            total += len(records)
            files += 1

        if day_offset % 180 == 0:
            print(f"  {date_str} generated...")

    print(f"  OK - {files:,} files, {total:,} weather records")
    return total, files

if __name__ == "__main__":
    print("=" * 55)
    print("  Maritime Lakehouse - WEATHER JSON Generator")
    print("  Output: output_files/landing/files/weather/")
    print("=" * 55)
    total, files = generate_all_weather()
    print("\n" + "=" * 55)
    print("  Generation complete!")
    print(f"  - Weather files : {files:,}")
    print(f"  - Weather records: {total:,}")
    print("  Upload folder: output_files/landing/files/weather/")
    print("=" * 55)
