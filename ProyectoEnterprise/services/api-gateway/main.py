import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("api-gateway")

# --- Configuration ---
PLC_URL = os.getenv("PLC_URL", "http://plc-service:8000")
AUTH_URL = os.getenv("AUTH_URL", "http://auth-service:8001")
ALARM_URL = os.getenv("ALARM_URL", "http://alarm-service:8002")
HISTORIAN_URL = os.getenv("HISTORIAN_URL", "http://historian-service:8003")
AI_URL = os.getenv("AI_URL", "http://ai-service:8004")
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")

# --- Globals ---
http_client = httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_connections=200))
connected_clients = set()
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "GATEWAY_WS_BRIDGE")
main_loop = None

def on_mqtt_message(client, userdata, msg):
    if not connected_clients or not main_loop: return
    try:
        payload = json.loads(msg.payload.decode())
        # Broadcast via WebSockets in the main event loop
        asyncio.run_coroutine_threadsafe(broadcast_ws(payload), main_loop)
    except Exception as e:
        logger.error(f"WS Bridge Error: {e}")

async def broadcast_ws(payload):
    # Create a copy to avoid Set changed size during iteration
    for ws in list(connected_clients):
        try:
            await ws.send_json(payload)
        except Exception as e:
            logger.warning(f"Failed to send to WS client, removing: {e}")
            if ws in connected_clients:
                connected_clients.remove(ws)

mqtt_client.on_message = on_mqtt_message

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    
    # Startup MQTT
    try:
        logger.info(f"📡 Gateway: Connecting to MQTT at {MQTT_BROKER}...")
        mqtt_client.connect(MQTT_BROKER, 1883, 60)
        mqtt_client.subscribe("enterprise/machine/state")
        mqtt_client.subscribe("enterprise/alarms")
        mqtt_client.loop_start()
        logger.info(f"✅ Gateway: MQTT connected.")
    except Exception as e:
        logger.error(f"❌ Gateway: MQTT Connection failed: {e}")
    
    yield
    
    # Shutdown
    mqtt_client.loop_stop()
    await http_client.aclose()

app = FastAPI(title="Enterprise API Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSockets ---
@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("⚡ WS Attempt: Incoming connection...")
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"✅ WS Client Connected. Total: {len(connected_clients)}")
    try:
        while True:
            # Keep alive and check for client disconnect
            await websocket.receive_text() 
    except WebSocketDisconnect:
        logger.info("ℹ️ WS Client Disconnected")
    except Exception as e:
        logger.error(f"⚠️ WS Connection Error: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

# --- Proxies ---
async def proxy_request(method: str, url: str, request: Request):
    try:
        content = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        
        r = await http_client.request(
            method=method,
            url=url,
            content=content,
            headers=headers,
            params=request.query_params
        )
        
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.json())
        return r.json()
    except httpx.RequestError as e:
        logger.error(f"Proxy Link Error ({url}): {e}")
        raise HTTPException(status_code=502, detail="Upstream service unreachable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Proxy Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Gateway Error")

@app.post("/auth/token")
async def proxy_login(request: Request):
    return await proxy_request("POST", f"{AUTH_URL}/token", request)

@app.get("/auth/users/me")
async def proxy_me(request: Request):
    return await proxy_request("GET", f"{AUTH_URL}/users/me", request)

@app.get("/plc/state")
async def proxy_plc_state(request: Request):
    return await proxy_request("GET", f"{PLC_URL}/state", request)

@app.post("/plc/command/{button}")
async def proxy_plc_cmd(button: str, request: Request):
    return await proxy_request("POST", f"{PLC_URL}/command/{button}", request)

@app.post("/plc/simulate/inject-fault/{fault_type}")
async def proxy_fault(fault_type: str, request: Request):
    return await proxy_request("POST", f"{PLC_URL}/simulate/inject-fault/{fault_type}", request)

@app.get("/alarms/alarms/active")
async def proxy_alarms_active(request: Request):
    return await proxy_request("GET", f"{ALARM_URL}/alarms/active", request)

@app.get("/alarms/alarms/history")
async def proxy_alarms_history(request: Request):
    return await proxy_request("GET", f"{ALARM_URL}/alarms/history", request)

@app.get("/ai/insights")
async def proxy_ai(request: Request):
    return await proxy_request("GET", f"{AI_URL}/ai/status", request)

@app.get("/metrics")
async def gateway_metrics():
    return {
        "status": "online",
        "connected_ws": len(connected_clients),
        "mqtt_connected": mqtt_client.is_connected()
    }

@app.get("/history/telemetry")
async def proxy_history_telemetry(request: Request):
    return await proxy_request("GET", f"{HISTORIAN_URL}/history/telemetry", request)

if __name__ == "__main__":
    import uvicorn
    # Use standard uvicorn features for WebSockets
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
