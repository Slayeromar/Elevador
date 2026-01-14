import json
import logging
import os
import time
from datetime import datetime
from threading import Thread
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("alarm-service")

# --- Config ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = 1883
PLC_SERVICE_URL = os.getenv("PLC_SERVICE_URL", "http://plc-service:8000")

# --- Alarm Engine Logic ---
class AlarmEngine:
    def __init__(self):
        self.active_alarms = {}
        self.history = []
        self.last_mc1 = False
        self.last_mc2 = False
        self.move_start_time = None

    def trigger_alarm(self, code, message, severity, client):
        if code not in self.active_alarms:
            evt = {
                "code": code,
                "message": message,
                "severity": severity,
                "timestamp": datetime.now().isoformat()
            }
            self.active_alarms[code] = evt
            self.history.insert(0, evt)
            if len(self.history) > 100: self.history.pop()
            
            logger.error(f"🚨 {message}")
            try:
                client.publish("enterprise/alarms", json.dumps({
                    "event": "alarm",
                    "data": evt,
                    "timestamp": datetime.now().isoformat()
                }))
            except: pass

    def clear_alarm(self, code, client):
        if code in self.active_alarms:
            logger.info(f"✅ Alarma Recuperada: {code}")
            del self.active_alarms[code]

    def check_logic(self, state, client):
        mc1 = state.get("mc1", False)
        mc2 = state.get("mc2", False)
        ls1 = state.get("ls1", False)
        ls2 = state.get("ls2", False)

        # 1. Interlocking Protection (Critical)
        if mc1 and mc2:
            self.trigger_alarm("ERR_INTERLOCK", "Conflicto de Contactor: MC1 y MC2 activos simultáneamente.", "CRITICAL", client)

        # 2. Travel Timeout (Predictive)
        if (mc1 or mc2) and not (self.last_mc1 or self.last_mc2):
            self.move_start_time = time.time()
        
        if (mc1 or mc2) and self.move_start_time:
            if (time.time() - self.move_start_time) > 15: # 15 Segundos de viaje max
                self.trigger_alarm("ERR_TIMEOUT", "Tiempo de viaje excedido. Posible atasco o falla de tracción.", "WARNING", client)
        
        if not mc1 and not mc2:
            self.move_start_time = None

        self.last_mc1 = mc1
        self.last_mc2 = mc2

engine = AlarmEngine()

# --- MQTT Client Logic ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("event") == "machine.state.changed":
            state = payload["data"]
            engine.check_logic(state, client)
    except Exception as e:
        logger.error(f"Error processing alarm logic: {e}")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_message = on_message

def start_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.subscribe("enterprise/machine/state")
        logger.info("📡 Alarm Service subscribed to MQTT enterprise/machine/state")
        mqtt_client.loop_forever()
    except Exception as e:
        logger.error(f"MQTT Error in Alarm Service: {e}")

# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Iniciando Alarm Service...")
    Thread(target=start_mqtt, daemon=True).start()
    yield
    # Shutdown
    mqtt_client.disconnect()

app = FastAPI(title="Enterprise Alarm Service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.get("/alarms/active")
async def get_active():
    return list(engine.active_alarms.values())

@app.get("/alarms/history")
async def get_history():
    return engine.history

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando Alarm Service API en puerto 8002...")
    uvicorn.run(app, host="0.0.0.0", port=8002)
