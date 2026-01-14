# Event Model Definition

The Elevator Enterprise System utilizes an asynchronous event-driven model to ensure low-latency communication and system observability.

## 1. Event Schema
Every event transmitted through the Edge Gateway or Service Mesh must follow this structure:

```json
{
  "event_id": "UUID",
  "timestamp": "ISO8601",
  "source": "plc-gateway | auth-service | ...",
  "type": "STATE_CHANGE | ALARM | AUDIT",
  "payload": { ... }
}
```

## 2. Core Industrial Events
- `ELEVATOR_POS_UPDATE`: Real-time floor and door status.
- `ALARM_ACTIVE`: Critical fault detected in hardware.
- `MAINTENANCE_REQUIRED`: Condition-based monitoring trigger.

## 3. Propagation Flow
1. **Source**: PLC updates a tag.
2. **Edge**: PLC Gateway detects the change and publishes an event.
3. **IT**: Services subscribe to relevant event types.
4. **HMI**: Real-time visualization via WebSockets.
