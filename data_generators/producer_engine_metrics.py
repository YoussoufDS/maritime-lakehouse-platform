"""
Maritime Lakehouse Platform
Producer Event Hubs - Engine Metrics Stream
Simule des capteurs IoT Wartsila/Kongsberg
Topic : engine-metrics-stream
"""

import json
import random
import time
from datetime import datetime
from azure.eventhub import EventHubProducerClient, EventData

random.seed(99)

# ─── CONFIG ───────────────────────────────────────────────
EVENT_HUB_CONN = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
EVENT_HUB_NAME = "engine-metrics-stream"
SEND_INTERVAL_SEC = 60   # Toutes les 60 secondes
BATCH_SIZE        = 20   # 20 navires par batch

# ─── DONNEES DE BASE ──────────────────────────────────────
VESSEL_IDS    = list(range(1, 151))
ENGINE_MODELS = ["Wartsila 12RT-flex96C","MAN B&W 12S90ME-C",
                 "Wartsila 6X62","MAN B&W 6S70MC","Wartsila 9L32"]

vessel_engine_state = {}
for vid in VESSEL_IDS:
    vessel_engine_state[vid] = {
        "rpm"         : random.uniform(60, 120),
        "temp_exhaust": random.uniform(300, 450),
        "temp_coolant": random.uniform(75, 95),
        "pressure_lube": random.uniform(3.5, 5.5),
        "power_kw"    : random.uniform(5000, 25000),
        "engine_model": random.choice(ENGINE_MODELS),
        "anomaly_prob": 0.02
    }

def update_engine(state):
    """Simule les variations des metriques moteur"""
    state["rpm"]          = max(0, state["rpm"] + random.uniform(-3, 3))
    state["temp_exhaust"] = max(200, state["temp_exhaust"] + random.uniform(-5, 5))
    state["temp_coolant"] = max(60, state["temp_coolant"] + random.uniform(-1, 1))
    state["pressure_lube"]= max(2, state["pressure_lube"] + random.uniform(-0.1, 0.1))
    state["power_kw"]     = max(0, state["power_kw"] + random.uniform(-200, 200))
    is_anomaly = random.random() < state["anomaly_prob"]
    if is_anomaly:
        state["temp_exhaust"] += random.uniform(50, 150)
    return state, is_anomaly

def create_engine_message(vessel_id):
    state, is_anomaly = update_engine(vessel_engine_state[vessel_id])
    vessel_engine_state[vessel_id] = state

    alert_type = None
    severity   = "normal"
    if is_anomaly:
        alert_type = random.choice([
            "HIGH_EXHAUST_TEMP",
            "LOW_LUBE_PRESSURE",
            "RPM_FLUCTUATION",
            "COOLANT_TEMP_HIGH"
        ])
        severity = random.choice(["warning","critical"])

    fuel_rate = round(state["power_kw"] * 0.00022, 2)

    return {
        "message_type"      : "ENGINE_METRICS",
        "vessel_id"         : vessel_id,
        "timestamp"         : datetime.utcnow().isoformat() + "Z",
        "engine_model"      : state["engine_model"],
        "rpm"               : round(state["rpm"], 1),
        "power_kw"          : round(state["power_kw"], 1),
        "exhaust_temp_c"    : round(state["temp_exhaust"], 1),
        "coolant_temp_c"    : round(state["temp_coolant"], 1),
        "lube_pressure_bar" : round(state["pressure_lube"], 2),
        "fuel_flow_rate_kg_h": fuel_rate,
        "running_hours"     : round(random.uniform(1000, 80000), 0),
        "is_anomaly"        : is_anomaly,
        "alert_type"        : alert_type,
        "severity"          : severity,
        "sensor_health"     : "OK" if not is_anomaly else "ALERT",
        "source"            : "WARTSILA_IoT_GATEWAY"
    }

def send_batch(producer):
    vessel_sample = random.sample(VESSEL_IDS, min(BATCH_SIZE, len(VESSEL_IDS)))
    event_batch   = producer.create_batch()
    for vessel_id in vessel_sample:
        msg  = create_engine_message(vessel_id)
        data = EventData(json.dumps(msg))
        event_batch.add(data)
    producer.send_batch(event_batch)
    return len(vessel_sample)

def main():
    print("=" * 55)
    print("  Maritime Lakehouse - Engine Metrics Producer")
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
                      f"Sent {count} engine metrics | Total: {total_sent:,}")
                time.sleep(SEND_INTERVAL_SEC)
            except KeyboardInterrupt:
                print(f"\n  Stopped. Total sent: {total_sent:,}")
                break
            except Exception as e:
                print(f"  Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    main()
