# Fabric Data Agent Configuration Guide

This directory contains the instruction sets and configuration for the Fabric Data Agent. Below are the scope and limitations for each configuration component.

## 📋 Configuration Scope & Limits

| Component | Character Limit | Description |
| :--- | :--- | :--- |
| **Agent Instructions** | 15,000 | Core system prompt guiding the agent's behavior and source selection. |
| **Data Source Description** | 800 | High-level summary of what the data represents and its use cases. |
| **Data Source Instructions** | 15,000 | Detailed mapping and business logic for a specific data source. |
| **Example Queries** | Q: 1,000 / SQL: 5,000 | Natural language/SQL pairs to guide the agent's query generation. |

---

## 📂 File Mapping

- **Agent Instructions**: See `[agent_instructions.md](file:///c:/Users/Anna.YR.Chen/Projects/sales_agent/docs/da_instructions/agent_instructions.md)`
- **Data Source Description**: See `[source_description.md](file:///c:/Users/Anna.YR.Chen/Projects/sales_agent/docs/da_instructions/source_description.md)`
- **Data Source Instructions**: See `[source_instructions.md](file:///c:/Users/Anna.YR.Chen/Projects/sales_agent/docs/da_instructions/source_instructions.md)`
- **Example Queries**: See `[example_queries.json](file:///c:/Users/Anna.YR.Chen/Projects/sales_agent/docs/da_instructions/example_queries.json)`

## 🎯 Objective
The goal of these instructions is to ensure the Data Agent provides accurate, business-aligned SQL queries and summaries for sales performance analysis across Billing and Booking datasets.