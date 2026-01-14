# Enterprise Architecture Blueprint

This document outlines the architectural principles and design patterns implemented in the Elevator Enterprise System.

## 1. Modular Decoupling
The system is divided into four strictly isolated domains:
- **OT (Operational Technology)**: Real-time control logic.
- **Edge**: The frontier between OT and IT.
- **Services (IT)**: Business logic, data persistence, and orchestration.
- **HMI**: Human-Machine Interface for visualization.

## 2. Communication Strategy
- **Internal (SCL)**: Synchronous high-speed logic within the PLC.
- **Inter-Layer (Gateway)**: Protocol translation from binary/industrial protocols to standard IT formats (JSON/Protobuf).
- **Service Mesh**: Future-ready internal communication within the IT layer.

## 3. Scalability Model
The system uses a container-first approach. Every service in `/services` is stateless where possible, allowing horizontal scaling using Kubernetes HPA (Horizontal Pod Autoscaler).

## 4. Observability by Design
No service is "black-boxed". Every component exposes metrics or logs that are ingested by the Observability stack (Prometheus/Grafana).
