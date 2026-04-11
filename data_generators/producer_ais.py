"""
Maritime Lakehouse Platform
Producer Event Hubs - AIS Positions Stream
Simule un feed AIS (MarineTraffic/exactEarth)
Topic : ais-positions-stream
"""

import json
import random
import time
from datetime import datetime
from azure.eventhub import EventHubProducerClient, EventData

random.seed(42)

# ─── CONFIG ───────────────────────────────────────────────
EVENT_HUB_CONN = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
EVENT_HUB_NAME = "ais-positions-stream"
SEND_INTERVAL_SEC = 10   # Envoyer toutes les 10 secondes
BATCH_SIZE        = 15   # 15 navires par batch

# ─── DONNEES DE BASE ──────────────────────────────────────
VESSEL_IDS = list(range(1, 151))

AIS_STATUSES = [
    "Under way using engine",
    "At anchor",
    "Moored",
    "Under way sailing",
    "Restricted manoeuvrability",
    "Not under command"
]

ROUTES = [
    {"name": "North Atlantic",  "lat": (45, 60),   "lon": (-60, -10)},
    {"name": "Mediterranean",   "lat": (30, 46),   "lon": (-5,  36)},
    {"name": "Asia Pacific",    "lat": (1,  35),   "lon": (100, 145)},
    {"name": "Indian Ocean",    "lat": (-10, 20),  "lon": (50,  90)},
    {"name": "North Sea",       "lat": (51, 61),   "lon": (-4,  10)},
    {"name": "Gulf of Mexico",  "lat": (18, 30),   "lon": (-98, -80)},
    {"name": "South America",   "lat": (-35, 0),   "lon": (-80, -35)},
]

vessel_positions = {}
for vid in VESSEL_IDS:
    route = random.choice(ROUTES)
    vessel_positions[vid] = {
        "lat": random.uniform(*route["lat"]),
        "lon": random.uniform(*route["lon"]),
        "heading": random.uniform(0, 360),
        "speed":   random.uniform(8, 18),
        "route":   route["name"]
    }

def update_position(pos):
    """Simule le mouvement du navire"""
    heading_rad = pos["heading"] * 3.14159 / 180
    import math
    distance_deg = pos["speed"] * SEND_INTERVAL_SEC / 3600 / 60
    pos["lat"]     = pos["lat"] + distance_deg * math.cos(heading_rad)
    pos["lon"]     = pos["lon"] + distance_deg * math.sin(heading_rad)
    pos["heading"] = (pos["heading"] + random.uniform(-5, 5)) % 360
    pos["speed"]   = max(0, min(25, pos["speed"] + random.uniform(-0.5, 0.5)))
    return pos

def create_ais_message(vessel_id):
    pos = vessel_positions[vessel_id]
    pos = update_position(pos)
    vessel_positions[vessel_id] = pos
    return {
        "message_type"      : "AIS_POSITION",
        "vessel_id"         : vessel_id,
        "imo_prefix"        : f"IMO{vessel_id:07d}",
        "timestamp"         : datetime.utcnow().isoformat() + "Z",
        "latitude"          : round(pos["lat"], 6),
        "longitude"         : round(pos["lon"], 6),
        "speed_over_ground" : round(pos["speed"], 1),
        "course_over_ground": round(pos["heading"], 1),
        "true_heading"      : round(pos["heading"], 1),
        "navigational_status": random.choice(AIS_STATUSES),
        "rate_of_turn"      : round(random.uniform(-10, 10), 1),
        "position_accuracy" : 1,
        "raim"              : False,
        "maritime_zone"     : pos["route"],
        "source"            : "AIS_TRANSPONDER",
        "mmsi"              : f"3{vessel_id:08d}"
    }

def send_batch(producer):
    vessel_sample = random.sample(VESSEL_IDS, min(BATCH_SIZE, len(VESSEL_IDS)))
    event_batch   = producer.create_batch()
    for vessel_id in vessel_sample:
        msg  = create_ais_message(vessel_id)
        data = EventData(json.dumps(msg))
        event_batch.add(data)
    producer.send_batch(event_batch)
    return len(vessel_sample)

def main():
    print("=" * 55)
    print("  Maritime Lakehouse - AIS Position Producer")
    print(f"  Event Hub : {EVENT_HUB_NAME}")
    print(f"  Interval  : every {SEND_INTERVAL_SEC}s")
    print(f"  Batch size: {BATCH_SIZE} vessels")
    print("  Press Ctrl+C to stop")
    print("=" * 55)

    if "YOUR_EVENTHUB" in EVENT_HUB_CONN:
        print("\n  ERROR: Update EVENT_HUB_CONN in this script")
        print("  Get it from: Azure Portal -> Event Hubs")
        print("  -> evhns-maritime-dev -> Shared access policies")
        return

    producer = EventHubProducerClient.from_connection_string(
        conn_str=EVENT_HUB_CONN,
        eventhub_name=EVENT_HUB_NAME
    )

    total_sent = 0
    with producer:
        while True:
            try:
                count = send_batch(producer)
                total_sent += count
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] "
                      f"Sent {count} AIS positions | Total: {total_sent:,}")
                time.sleep(SEND_INTERVAL_SEC)
            except KeyboardInterrupt:
                print(f"\n  Stopped. Total sent: {total_sent:,}")
                break
            except Exception as e:
                print(f"  Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    main()
