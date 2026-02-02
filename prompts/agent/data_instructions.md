# Sales Data Agent: Data Instructions (SOTA)

This document provides the foundational data architecture, column definitions, and business logic mapping for the Sales Data Agent.

## 1. Data Source Overview
The system utilizes two primary fact tables with **monthly aggregated data**. All queries should default to the most intuitive JOIN or FILTER structure without unnecessary complexity.

| Table Name | Schema | Semantic Purpose |
| :--- | :--- | :--- |
| `fact_monthly_sales_poa_billing` | `ods.` | **Billing (Actuals)**: Revenue, shipments, billed sales, and costs. |
| `fact_monthly_sales_poa_booking` | `ods.` | **Booking (Pipeline)**: Sales orders received, forward-looking demand. |

---

## 2. Table Selection & Logic Protocols
### 2.1 The "Billing-First" Rule
- **DEFAULT**: Always use `ods.fact_monthly_sales_poa_billing` for all general "POA", "Sales", or "Growth" queries.
- **EXCEPTION**: Use `ods.fact_monthly_sales_poa_booking` **ONLY** if the word "Booking" or "BOOK" is explicitly mentioned in the question.

### 2.2 Order Type Filtering
- **Standard Billing**: For any billing query not involving OTR or Backlog, use `WHERE order_type = 'SHIPMENT'`.
- **OTR (Order-to-Revenue)**: Include ALL `order_type` values (Remove the 'SHIPMENT' filter).
- **Backlog Definition**: Defined as `order_type <> 'SHIPMENT'` within the **Billing** table. **Never use the Booking table for Backlog.**

---

## 3. Data Dictionary (Schema & Values)

### 3.1 Dimensions
| Column Name | Category | Description / Constraints | Sample Values (Non-Exhaustive) |
| :--- | :--- | :--- | :--- |
| `year_month` | Time | Primary temporal filter (Format: `YYYYMM`). | `202412`, `202501` |
| `order_type` | Business | Filter Billing/Booking status. | `SHIPMENT`, `PAST DUE`, `BACKLOG`, `BOOKING` |
| `brand` | Product | Product brand names. | `YAGEO`, `PULSE`, `KEMET`, `CHILISIN`, `TOKIN` |
| `ru` | Region | Reporting Unit (Main region). | `AMERICAS`, `EMEA`, `GREAT CHINA`, `SOUTHEAST ASIA` |
| `pbg` | Product | Product Business Group (Top level). | `Capacitor`, `Resistors`, `Magnetics`, `SENSOR` |
| `pbu` | Product | Product Business Unit (Sub-type). | `MLCC`, `TANTALUM`, `R-Chip`, `Wireless` |
| `focus_flag`| Tracking | Indicator for focus products. | `Yes`, `No`, `Adjustment` |
| `customer_parent`| Customer | Primary customer (Invoiced). | `HON HAI`, `VALEO`, `GOOGLE`, `INFINEON` |
| `total_sales` | Metric | Financial value (USD). | `12345.67` |
| `total_qty` | Metric | Product volume (Units). | `5000` |
| `total_cost` | Metric | Cost of goods (Only for `SHIPMENT`).| `8000` |

> [!NOTE]
> **Generalization Rule**: The sample values above are representative but not exhaustive. If a user asks for a value NOT in this list (e.g., a specific customer name or a different brand), the Agent **MUST** still attempt to query it using the correct column. Do NOT assume a value is "invalid" just because it's missing from the sample list.

---

## 4. Business Ratios & Formulas (KISS Protocol)
Follow these simplified patterns for consistency.

### 4.1 Atomical Logic
- **Gross Profit (GP)**: `total_sales - total_cost`
- **Gross Margin % (GM%)**: `(total_sales - total_cost) / NULLIF(total_sales, 0)`
- **Average Price (ASP)**: `total_sales / NULLIF(total_qty, 0)`

### 4.2 Cross-Period Comparisons (MoM/QoQ/YoY)
Use simple CTEs to isolate periods before joining. Use `NULLIF` for all division.
- **Example MoM**: `(Curr - Prior) / NULLIF(Prior, 0)`

### 4.3 BB Ratio Patterns
- **Aggregation Pattern**: Calculate Booking and Billing totals independently (using separate CTEs). Avoid standard `INNER JOIN` on keys.
- **BB Ratio (Value)**: `BookingTotalSales / NULLIF(BillingTotalSales, 0)`
- **BB Qty Ratio (Volume)**: `BookingTotalQty / NULLIF(BillingTotalQty, 0)`

---

## 5. Constraints & Limitations
- **No Order Grain**: The database does NOT store individual order numbers or counts.
- **Explicit Dimensions**: DIMENSIONS (like `ru` or `brand`) should only be added to `GROUP BY` if explicitly asked. Do NOT hallucinate extra breakdowns.
- **Cost Integrity**: Costs are only valid for `'SHIPMENT'`. OTR cost equals Shipment cost.
