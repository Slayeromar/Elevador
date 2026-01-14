import json
import logging
import os
import sqlite3
from datetime import datetime
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("historian-service")

# --- Config ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
DB_PATH = "historian.db"

# --- Database ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS telemetry 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, position REAL, mc1 BOOLEAN, mc2 BOOLEAN, ls1 BOOLEAN, ls2 BOOLEAN)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS events 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, code TEXT, message TEXT, severity TEXT)''')
    conn.commit()
    conn.close()

def save_event(event_type, data):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        ts = datetime.now().isoformat()
        
        if event_type == 'machine.state.changed':
            cursor.execute("INSERT INTO telemetry (timestamp, position, mc1, mc2, ls1, ls2) VALUES (?, ?, ?, ?, ?, ?)",
                           (ts, data.get('pos'), data.get('mc1'), data.get('mc2'), data.get('ls1'), data.get('ls2')))
        elif event_type in ['alarm', 'alarm.predictive']:
            cursor.execute("INSERT INTO events (timestamp, code, message, severity) VALUES (?, ?, ?, ?)",
                           (ts, data.get('code'), data.get('message'), data.get('severity')))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving to Historian DB: {e}")
    finally:
        conn.close()

# --- MQTT Client ---
def on_connect(client, userdata, flags, reason_code, properties):
    logger.info(f"📡 Historian conectado al Broker (RC: {reason_code})")
    client.subscribe("enterprise/machine/state")
    client.subscribe("enterprise/alarms")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        event_type = payload.get("event", "unknown.event")
        save_event(event_type, payload.get("data", payload))
    except Exception as e:
        logger.error(f"Error processing historian message: {e}")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "HISTORIAN_SERVICE")
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()
    yield
    # Shutdown
    mqtt_client.loop_stop()

app = FastAPI(title="Industrial Historian Service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.get("/history/telemetry")
async def get_telemetry(limit: int = 100):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM telemetry ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/history/events")
async def get_events(limit: int = 50):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
