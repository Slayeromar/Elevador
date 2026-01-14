import asyncio
import json
import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ai-service")

# --- Config ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
HISTORIAN_URL = os.getenv("HISTORIAN_URL", "http://historian-service:8003")
AI_THRESHOLD = 1.25 

# State
current_run_start = None
travel_times = [] 
system_health_score = 100
ai_insights = "Analizando patrones de motor..."

# --- MQTT Setup ---
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "AI_PREDICTIVE_ENGINE")

def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe("enterprise/machine/state")
    logger.info("🧠 AI Engine: Suscrito al flujo de datos")

def on_message(client, userdata, msg):
    global current_run_start, travel_times, ai_insights, system_health_score
    try:
        data = json.loads(msg.payload.decode())
        if data.get("event") == "machine.state.changed":
            state = data["data"]
            mc1, mc2 = state.get("mc1"), state.get("mc2")

            if (mc1 or mc2) and current_run_start is None:
                current_run_start = datetime.now()
            elif not mc1 and not mc2 and current_run_start is not None:
                duration = (datetime.now() - current_run_start).total_seconds()
                current_run_start = None
                if duration > 1.0: analyze_performance(duration, client)
    except Exception as e: logger.error(f"AI Logic Error: {e}")

def analyze_performance(duration, client):
    global ai_insights, system_health_score, travel_times
    if not travel_times:
        travel_times.append(duration)
        return

    avg_time = sum(travel_times) / len(travel_times)
    if duration > (avg_time * AI_THRESHOLD):
        system_health_score = max(0, system_health_score - 10)
        ai_insights = f"⚠️ ANOMALÍA: Viaje lento ({duration:.1f}s vs avg {avg_time:.1f}s)."
        client.publish("enterprise/alarms", json.dumps({
            "event": "alarm.predictive",
            "data": {"code": "PRED_MECH_WEAR", "message": ai_insights, "severity": "WARNING"},
            "timestamp": datetime.now().isoformat()
        }))
    else:
        system_health_score = min(100, system_health_score + 2)
        ai_insights = "Estado óptimo: Patrones consistentes."
    
    travel_times.append(duration)
    if len(travel_times) > 50: travel_times.pop(0)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# --- App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_start()
    yield
    mqtt_client.loop_stop()

app = FastAPI(title="Enterprise AI Analytics", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.get("/ai/status")
async def get_ai_status():
    return {
        "health_score": system_health_score,
        "insights": ai_insights,
        "avg_travel_time": round(sum(travel_times)/len(travel_times), 2) if travel_times else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
