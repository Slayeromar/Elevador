# Elevador Enterprise Automation

An industry-grade blueprint for modern Industrial Automation (CES 2026), demonstrating OT/IT convergence, Cloud-Native architecture, and Enterprise governance.

## Executive Summary

This project serves as a professional reference for scaling industrial control systems. It transitions from a traditional monolithic PLC approach to a distributed, event-driven architecture that is observable, secure, and scalable.

### Key Pillars
- **Zero Trust Security**: IAM-based access control and encrypted communication between OT and IT layers.
- **Microservices Orchestration**: Fully containerized services using Docker/Kubernetes.
- **Event-Driven Architecture**: Asynchronous communication enabling real-time status updates and historiography.
- **Edge Computing**: Gateway layer designed for protocol translation (OPC UA to MQTT/WebSockets).

## System Architecture

```mermaid
graph TD
    %% ==========================================
    %% 1. DEFINICIÓN DE ESTILOS (AESTHETICS)
    %% ==========================================
    classDef ot_node fill:#1a365d,stroke:#3182ce,stroke-width:2px,color:#fff,rx:5;
    classDef edge_node fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#fff,rx:5;
    classDef bus_node fill:#7c2d12,stroke:#ea580c,stroke-width:2px,color:#fff,rx:10;
    classDef svc_node fill:#0f172a,stroke:#38bdf8,stroke-width:1px,color:#fff,rx:5;
    classDef data_node fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff,rx:5;
    classDef ai_node fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#fff,rx:5;
    classDef ui_node fill:#020617,stroke:#38bdf8,stroke-width:1px,color:#fff,rx:5;
    classDef threat fill:#7f1d1d,stroke:#ef4444,stroke-width:1px,color:#fff,stroke-dasharray: 5 5;
    %% ==========================================
    %% 2. CAPA OT: CONTROL DETERMINÍSTICO
    %% ==========================================
    subgraph Layer_OT ["OPERATIONAL TECHNOLOGY (OT) - Deterministic Logic"]
        direction TB
        PLC["Siemens S7-1500 PLC <br/>(SCL Logic Engine)"]:::ot_node
        Field["Industrial Sensors/Actuators <br/>(Variable Frequency Drives, Load Cells)"]:::ot_node
        PLC <-->|Hard-Wired I/O| Field
    end
    %% ==========================================
    %% 3. CAPA EDGE: PROTOCOL TRANSLATION
    %% ==========================================
    subgraph Layer_Edge ["INDUSTRIAL EDGE - Gateway Layer"]
        GW["PLC Gateway Gateway <br/>(Snap7 / OPC UA Client)"]:::edge_node
        Buffer["Resilience Buffer <br/>(Local Queue)"]:::edge_node
        GW --- Buffer
    end
    %% ==========================================
    %% 4. BACKBONE: EVENT-DRIVEN BUS
    %% ==========================================
    subgraph Layer_Bus ["ENTERPRISE EVENT BUS - Async Communications"]
        Broker["MQTT / Pub-Sub Broker <br/>(The System Backbone)"]:::bus_node
    end
    %% ==========================================
    %% 5. CAPA IT: CLOUD-NATIVE MICROSERVICES
    %% ==========================================
    subgraph Layer_IT ["ENTERPRISE IT - Service Mesh (Docker/K8s)"]
        direction LR
        APIGW["API Gateway <br/>(FastAPI / Security)"]:::svc_node
        Auth["Auth Service <br/>(Zero Trust / JWT)"]:::svc_node
        PLCSvc["PLC Service <br/>(State Coordinator)"]:::svc_node
        AlarmSvc["Alarm Service <br/>(Critical Logic)"]:::svc_node
        HistSvc["Historian Service <br/>(Data Ingestion)"]:::svc_node
        
        APIGW <---> Auth
    end
    %% ==========================================
    %% 6. CAPA DATA & AI: INTELLIGENCE
    %% ==========================================
    subgraph Layer_Data ["DATA & INTELLIGENCE - Insight Layer"]
        DB["PostgreSQL / TimescaleDB <br/>(Persistent Event Store)"]:::data_node
        AI["Inference Engine <br/>(Vertex AI / Anomaly Detection)"]:::ai_node
    end
    %% ==========================================
    %% 7. CAPA HMI: OPERATOR EXPERIENCE
    %% ==========================================
    subgraph Layer_UI ["HMI & OBSERVABILITY - Stateless UX"]
        Web["Web HMI <br/>(React / WebSockets)"]:::ui_node
        Obs["Monitoring Stack <br/>(Prometheus / Grafana)"]:::ui_node
    end
    %% ==========================================
    %% FLUJOS DE DATOS (DATA FLOWS)
    %% ==========================================
    
    %% Upbound: Sensor a Nube
    PLC ---->|S7 Protocol| GW
    GW ---->|JSON Events| Broker
    Broker -.->|Subscribe| PLCSvc
    Broker -.->|Subscribe| AlarmSvc
    Broker -.->|Subscribe| HistSvc
    HistSvc ===>|Stream| DB
    
    %% IQ Flow: Inteligencia
    DB ---->|Analysis| AI
    AI -.->|Predictive Event| Broker
    
    %% Downbound: Comando de Usuario
    Web <---->|Secure WS/REST| APIGW
    APIGW <--->|Validate Orchestration| PLCSvc
    PLCSvc ---->|Command Event| Broker
    Broker -.->|Subscribe| GW
    GW ---->|Write Tag| PLC
    %% Transversal: Seguridad
    Security["Zero Trust Governance: <br/>Secrets, Audit Logs, Vault"]:::threat
    Security -.-> Layer_Edge
    Security -.-> Layer_IT
    Security -.-> Layer_UI
    %% Metrics
    PLCSvc -.->|Scrape| Obs
    HistSvc -.->|Query| Obs
```

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **OT** | TIA Portal, SCL, S7-PLCSIM Advanced |
| **Logic/Services** | Python 3.11+, FastAPI, Docker |
| **Storage** | Prometheus (Time-series), Historian (Custom JSON/SQL) |
| **Frontend** | Vanilla JS/React (Stateless/Real-time) |
| **Infra** | Docker Compose, Kubernetes (Ready) |

## Use Cases
1. **Predictive Maintenance**: Data extraction for ML-based fault detection.
2. **Multi-Plant Monitoring**: Scalable historian service for fleet management.
3. **Advanced Security Auditing**: Centralized logging for industrial compliance.

## Technical Roadmap
- [ ] Phase 1: Real-time synchronization and HMI parity.
- [ ] Phase 2: Integration of AI-driven anomaly detection.
- [ ] Phase 3: Global deployment via Kubernetes (K8s) clusters.

---
> [!IMPORTANT]
> This repository is a professional blueprint. All architectural decisions prioritize reliability and security over academic simplicity.
