# Operational Technology (OT) Layer

This directory contains the real-time control logic for the Elevator Enterprise System.

## Contents
- **plc/scl/**: Structured Control Language source files for Siemens S7-1500.
- **plc/tag-tables/**: Exported TIA Portal tag tables (XLSX/XML).
- **plc/ladder/**: Graphical logic representations (if applicable).

## Implementation Rules
1. **Separation of Concerns**: This layer MUST NOT contain any high-level code (Python, JavaScript).
2. **Determinism**: Logic implemented here follows cyclical execution standards (OB1) to ensure industrial reliability.
