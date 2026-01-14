import asyncio
import json
import logging
import os
import time
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from snap7.util import get_bool, set_bool
import snap7
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("plc-service")

# --- PROMETHEUS METRICS (Enterprise Standards) ---
# Operational Metrics
PLC_SCAN_TIME = Histogram('plc_scan_time_seconds', 'Industrial scan cycle time', buckets=(.005, .01, .025, .05, .075, .1, .25))
TOTAL_WORK_CYCLES = Counter('plc_work_cycles_total', 'Total completed elevator trips')
UPTIME_SECONDS = Counter('plc_uptime_seconds_total', 'Total service operation time')

# Health Metrics
PLC_CPU_LOAD = Gauge('plc_cpu_load_percent', 'Simulated PLC CPU utilization')
PLC_MEM_USAGE = Gauge('plc_memory_usage_bytes', 'Simulated PLC Memory consumption')
MOTOR_TEMP = Gauge('plc_motor_temperature_celsius', 'Real-time motor thermal state')
ELEVATOR_POS = Gauge('plc_elevator_position', 'Current elevator height (0-1)')

# Command Metrics
COMMANDS_TOTAL = Counter('plc_commands_received_total', 'Total commands sent from HMI', ['command'])

# --- Config ---
PLC_IP = os.getenv("PLC_IP", "192.168.0.11")
DB_NUMBER = int(os.getenv("DB_NUMBER", "1"))
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")
MQTT_TOPIC = "enterprise/machine/state"

class ElevatorPhysics:
    def __init__(self):
        self.position = 0.0
        self.speed = 0.012
        self.faults = set()
        self.last_inputs = {}
        self.last_pos = 0.0
        self.direction = 0 # 1 up, -1 down, 0 idle
        self.lock = asyncio.Lock()
        self.start_time = time.time()

physics = ElevatorPhysics()

# --- MQTT Setup ---
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "PLC_SERVICE_GATEWAY")

def connect_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, 1883, 60)
        mqtt_client.loop_start()
        logger.info(f"📡 PLC Service connected to MQTT at {MQTT_BROKER}")
    except Exception as e:
        logger.error(f"MQTT Connection Error: {e}")

class PLCManager:
    def __init__(self, ip):
        self.client = snap7.client.Client()
        self.ip = ip

    def connect(self):
        if not self.client.get_connected():
            try: self.client.connect(self.ip, 0, 1)
            except: pass

    def read_db(self):
        self.connect()
        try: return self.client.db_read(DB_NUMBER, 0, 1)
        except: return None

    async def write_input_bit(self, bit, value):
        if physics.last_inputs.get(bit) == value: return
        async with physics.lock:
            self.connect()
            try:
                data = self.client.db_read(DB_NUMBER, 0, 1)
                set_bool(data, 0, bit, value)
                self.client.db_write(DB_NUMBER, 0, data)
                physics.last_inputs[bit] = value
            except: pass

plc = PLCManager(PLC_IP)

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_mqtt()
    loop_task = asyncio.create_task(main_loop())
    yield
    loop_task.cancel()
    mqtt_client.loop_stop()

app = FastAPI(title="Industrial PLC Service", lifespan=lifespan)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/state")
def get_state():
    data = plc.read_db()
    if data:
        return {
            "bp1": get_bool(data, 0, 0), "bp2": get_bool(data, 0, 1),
            "ls1": get_bool(data, 0, 2), "ls2": get_bool(data, 0, 3),
            "mc1": get_bool(data, 0, 4), "mc2": get_bool(data, 0, 5),
            "l1": get_bool(data, 0, 6), "l2": get_bool(data, 0, 7),
            "pos": round(physics.position, 3),
            "timestamp": datetime.now().isoformat()
        }
    raise HTTPException(status_code=503, detail="PLC unreachable")

@app.post("/command/{button}")
async def send_command(button: str, value: bool):
    COMMANDS_TOTAL.labels(command=button).inc()
    mapping = {"bp1": 0, "bp2": 1}
    if button in mapping:
        await plc.write_input_bit(mapping[button], value)
        return {"status": "ok"}
    return {"status": "error"}

@app.post("/simulate/inject-fault/{fault_type}")
async def inject_fault(fault_type: str):
    if fault_type == "reset":
        physics.faults.clear()
        physics.position = 0.0
        await plc.write_input_bit(2, True)
        await plc.write_input_bit(3, False)
    else:
        physics.faults.add(fault_type)
    return {"status": "injected"}

async def main_loop():
    last_loop_time = time.time()
    while True:
        start_scan = time.time()
        try:
            # Update Uptime
            UPTIME_SECONDS.inc(0.05)
            
            # Simulate PLC Health Metrics
            PLC_CPU_LOAD.set(15.5 + (physics.position * 10.0)) # CPU rises as motor works
            PLC_MEM_USAGE.set(1024 * 1024 * 4 + (len(physics.faults) * 1024))
            
            data = plc.read_db()
            if data and "jam" not in physics.faults:
                mc1 = get_bool(data, 0, 4)
                mc2 = get_bool(data, 0, 5)

                # Physics
                if mc1 and physics.position < 1.0:
                    physics.position = min(1.0, physics.position + physics.speed)
                elif mc2 and physics.position > 0.0:
                    physics.position = max(0.0, physics.position - physics.speed)

                ELEVATOR_POS.set(physics.position)
                MOTOR_TEMP.set(24.0 + (physics.position * 5.0) + (10.0 if mc1 or mc2 else 0.0))

                # Limit Switch Logic
                await plc.write_input_bit(2, True if physics.position <= 0.005 else False)
                await plc.write_input_bit(3, True if physics.position >= 0.995 else False)

                # Cycle Counting (When it reaches floor and was moving)
                if physics.position >= 0.995 and physics.last_pos < 0.995:
                    TOTAL_WORK_CYCLES.inc()
                elif physics.position <= 0.005 and physics.last_pos > 0.005:
                    TOTAL_WORK_CYCLES.inc()

                physics.last_pos = physics.position

                current_state = {
                    "bp1": get_bool(data, 0, 0), "bp2": get_bool(data, 0, 1),
                    "ls1": get_bool(data, 0, 2), "ls2": get_bool(data, 0, 3),
                    "mc1": mc1, "mc2": mc2, 
                    "l1": get_bool(data, 0, 6), "l2": get_bool(data, 0, 7),
                    "pos": round(physics.position, 2)
                }

                mqtt_client.publish(MQTT_TOPIC, json.dumps({
                    "event": "machine.state.changed",
                    "data": current_state,
                    "timestamp": datetime.now().isoformat()
                }))
        except Exception as e:
            logger.debug(f"Loop Error: {e}")
        
        # Scan Cycle Metric
        PLC_SCAN_TIME.observe(time.time() - start_scan)
        await asyncio.sleep(0.05)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
