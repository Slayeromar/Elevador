# Security & Governance Model

Industrial systems are increasingly targets of cyber threats. This system implements a "Defense in Depth" strategy.

## 1. Zero Trust Architecture
- **Never Trust, Always Verify**: No component (even internal) has implicit access to another.
- **Identity-First**: All microservices must authenticate via the `auth-service` using JWT or mutual TLS (mTLS).

## 2. Network Segmentation
- **OT Isolation**: The PLC resides in a dedicated VLAN, accessible only by the Edge Gateway via strict firewall rules.
- **Northbound Encryption**: All data leaving the industrial floor is encrypted using TLS 1.3.

## 3. Audit Logging
Every action that changes the system state (e.g., manual override, setpoint change) is immutable and stored in the Security Audit Log.
