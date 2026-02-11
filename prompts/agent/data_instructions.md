# Sales Data Agent: Data Instructions (SOTA)

This document provides the foundational data architecture, column definitions, and business logic mapping for the Sales Data Agent.

## 1. Data Source Overview
The system utilizes two primary fact tables with **monthly aggregated data**. All monetary values are in **USD**. All queries should default to the most intuitive JOIN or FILTER structure without unnecessary complexity.

| Table Name | Schema | Semantic Purpose |
| :--- | :--- | :--- |
| `fact_monthly_sales_poa_billing` | `ods.` | **Billing (Actuals)**: Revenue, shipments, billed sales, and costs. **(NO BUDGET COLUMNS)** |
| `fact_monthly_sales_poa_billing` | `ods.` | **Backlog**: DEFINED AS this table with `order_type <> 'SHIPMENT'`. **NEVER** use Booking table for Backlog. |
| `fact_monthly_sales_poa_booking` | `ods.` | **Booking (Pipeline)**: Sales orders received, forward-looking demand. |
| `fact_monthly_sales_poa_budget` | `ods.` | **Budget (Target)**: Financial targets. |

---

## 2. Table Selection & Logic Protocols
### 2.1 The "Billing-First" Rule
- **DEFAULT**: Always use `ods.fact_monthly_sales_poa_billing` for all general "POA", "Sales", or "Growth" queries.
- **EXCEPTION**: Use `ods.fact_monthly_sales_poa_booking` **ONLY** if the word "Booking" or "BOOK" is explicitly mentioned in the question.

### 2.2 Order Type Filtering
- **Standard Billing**: For any billing query not involving OTR or Backlog, use `WHERE order_type = 'SHIPMENT'`.
- **OTR (Order-to-Revenue)**: **CRITICAL**: "OTR" means **ALL** `order_type` values. Do NOT filter by `order_type`. Include EVERYTHING (Shipment, Backlog, etc.).
- **Backlog Definition**: Defined as `order_type <> 'SHIPMENT'` within the **Billing** table. **Never use the Booking table for Backlog.**
- **Budget Join Rule**: NEVER join on `order_type` when querying `ods.fact_monthly_sales_poa_budget`. The budget table does not contain valid `order_type` mapping for Billing types. Join only on `year_month`, `ru`, `customer_parent`, etc.

### 2.3 Budget Alignment Protocol (CRITICAL)
-   **Mapping**: Budget uses `sub_unit_cbr` instead of `sub_unit`. Join on `budget.sub_unit_cbr = billing.sub_unit`.
-   **Aggregate-First**: For queries at Region/PBG level, aggregate Billing first. For Customer level, direct join is allowed.
-   **Symmetric Customer Filter**: When filtering by "Customer" for Hit Rate, you **MUST** check `customer_parent`, `local_assembler`, AND `final_customer` in **BOTH** the Billing CTE and the Budget CTE.
-   **Symmetric Product Filter**: When filtering by "Product" (e.g. "Capacitor"), you **MUST** check `pbg`, `pbu`, `pbu_1`, AND `pbu_2` in **BOTH** the Billing CTE and the Budget CTE.
-   **Data Constraint**: Budget data is only available from **2025 onwards**. Queries for 2024 budget or earlier will return 0 or NULL for budget metrics. Inform the user if they ask for pre-2025 budget.

### 2.4 Anti-Hallucination Protocol (STRICT)
- **Billing Table Limitations**: The table `ods.fact_monthly_sales_poa_billing` **DOES NOT CONTAIN** `total_budget`.
- **Budget Rule**: You **MUST** join `ods.fact_monthly_sales_poa_budget` to get any budget data.
- **FAILURE CONDITION**: Any query that attempts to select `total_budget` from `ods.fact_monthly_sales_poa_billing` is a **CRITICAL HALLUCINATION** and will fail.
- **NO RECORD COUNTING**: Do **NOT** use `COUNT(*)` or `COUNT(1)` to report "Number of Orders" or "Transaction Volume". The data is aggregated; row count is meaningless business noise.




---

## 3. Data Dictionary (Schema & Values)

### 3.1 Dimensions
| Column Name | Category | Description / Constraints | Sample Values (Non-Exhaustive) |
| :--- | :--- | :--- | :--- |
| `year_month` | Time | Primary temporal filter (Format: `YYYY-MM`). | `2024-12`, `2025-01` |
| `order_type` | Business | Filter Billing/Booking status. | `SHIPMENT`, `PAST DUE`, `BACKLOG`, `BOOKING` |

| `ru` | Region | Reporting Unit (Main region). | `AMERICAS`, `EMEA`, `GREAT CHINA`, `SOUTHEAST ASIA` |
| `pbg` | Product | Product Business Group (Top level). | `Capacitor`, `Resistors`, `Magnetics`, `SENSOR` |
| `pbu` | Product | Product Business Unit (Sub-type). | `MLCC`, `TANTALUM`, `R-Chip`, `Wireless` |
| `pbu_1` | Product | Product hierarchy level 1. | `COMMODITY`, `HIGH CAP` |
| `pbu_2` | Product | Product hierarchy level 2. | `Ceramic`, `METAL` |
| `local_assembler` | Customer | Secondary customer view (Assembler). | `FLEX`, `HON HAI` |
| `final_customer` | Customer | End-user customer view. | `APPLE`, `TESLA` |
| `g7` | Channel | Channel / Distributor details. | `AVNET`, `Non-G7` |
| `focus_flag`| Tracking | Indicator for focus products. | `Yes`, `No`, `Adjustment` |
| `fu_global_ems_flag` | Tracking | Global EMS account indicator. | `Yes`, `No` |
| `fu_us_oem_flag` | Tracking | US OEM account indicator. | `Yes`, `No` |
| `fu_emea_oem_flag` | Tracking | EMEA OEM account indicator. | `Yes`, `No` |
| `customer_parent`| Customer | Primary customer (Invoiced). | `HON HAI`, `VALEO`, `GOOGLE`, `INFINEON` |
| `g7_flag` | Tracking | G7 Country indicator (Renamed from fu_g7_flag). | `Yes`, `No` |
| `total_sales` | Metric | Financial value (USD). | `12345.67` |
| `total_qty` | Metric | Product volume (Units). | `5000` |
| `total_cost` | Metric | Cost of goods (Only for `SHIPMENT`).| `8000` |
| `total_budget` | Metric | Budget Target (USD). Available in Budget Table ONLY. | `50000.00` |

> [!NOTE]
> **Generalization Rule**: The sample values above are representative but not exhaustive. If a user asks for a value NOT in this list (e.g., a specific customer name or a different brand), the Agent **MUST** still attempt to query it using the correct column. Do NOT assume a value is "invalid" just because it's missing from the sample list.

### 3.3 Triple-Net Entity Resolution Protocol (SOTA)
**Strategy**: (1) LLM Intelligence -> (2) Pareto List -> (3) SQL Fallback.

#### Protocol Steps
1.  **Net 1: Internal Knowledge (LLM)**
    -   Use your pre-trained knowledge to correct obvious industry typos *before* generating SQL.
    -   **Example**: User types "Compel" -> You know it's "COMPAL" -> Generate SQL for `COMPAL`.
    -   **Example**: User types "Foxcon" -> You know it's "FOXCONN".

2.  **Net 2: Pareto Reference Lists (Top 20)**
    -   Check the "Top Reference Lists" below. If exact match found, use `=`,
    -   **Example**: `ru = 'GREAT CHINA'`.

3.  **Net 3: SQL Fallback (SOUNDEX + Wildcard)**
    -   **Condition**: If the entity is NOT in the reference list AND you are not 100% sure of the correction.
    -   **Action**: You **MUST** use a performance-optimized fuzzy search combining `LIKE` and `SOUNDEX`.
    -   **Pattern**: `WHERE (col LIKE '%Input%' OR SOUNDEX(col) = SOUNDEX('Input'))`
    -   *Why?* `SOUNDEX` is faster than `DIFFERENCE` and catches phonetic typos (e.g. "Simens" matches "Siemens").

4.  **Net 4: Quad-Net Product Search (Broadest Coverage)**
    -   **Rule**: When searching for ANY product name (e.g., "MLCC", "Resistor", "High Cap"), you **MUST** search across ALL product hierarchy columns (`pbg`, `pbu`, `pbu_1`, `pbu_2`).
    -   **CRITICAL OVERRIDE**: Even if a value is listed in "Section 3.1" under a specific column (e.g., `pbu`), you **MUST** still search ALL 4 columns. Do NOT assume the column.
    -   **Pattern (Billing & Budget)**: `WHERE (pbg = 'Input' OR pbu = 'Input' OR pbu_1 = 'Input' OR pbu_2 = 'Input')`

#### A. Global Synonyms & Mappings
| User Input / Synonym | Correct SQL Logic (Target Values) |
| :--- | :--- |
| **"GREATER CHINA"**, "G. China", "GC" | `ru = 'GREAT CHINA'` |
| **"SE ASIA"**, "ASEAN" | `ru = 'SOUTHEAST ASIA'` |
| **"N. AMERICA"**, "North America" | `ru = 'AMERICAS'` (unless sub-region specified) |
| **"Japan and Korea"**, "JP/KR", "Japan & Korea" | `ru = 'JAPAN & KOREA'` |
| **"APAC"**, "Asia Pacific" | `ru IN ('SOUTHEAST ASIA', 'GREAT CHINA', 'JAPAN & KOREA')`|
| **"TMSS"** | `pbu = 'Telemecanique'` |
| **"GEMS"** | `fu_global_ems_flag = 'Yes'` (Global EMS) |

#### B. Top Reference Lists (Pareto - Not Exhaustive)
> **Note**: These lists contain updated values from sample data. Use Quad-Net search for products.

**1. Reporting Units (ru)**
`GREAT CHINA`, `EMEA`, `AMERICAS`, `SOUTHEAST ASIA`, `OTHERS`, `JAPAN & KOREA`

**2. Product Hierarchy (PBG)**
`Capacitor`, `Resistors`, `Magnetics`, `SENSOR`, `OTHER`

**3. Regional Sub-Units (sub_unit)**
`CHINA`, `AMERICAS G7`, `EMEA`, `OTHERS`, `TAIWAN`, `MALAYSIA`, `JAPAN`, `SOUTH EUROPE`, `AMERICAS SOUTH`, `KOREA`, `EMEA GLOBAL OEMS`, `WEST EUROPE & HIGH RELIABILITY`, `SE ASIA-G7`, `SINGAPORE/OEMS`, `SOUTHEAST ASIA`, `CENTRAL EUROPE`, `AMERICAS`, `INDIA`, `THAILAND`, `JAPANESE OEMS`, `NORTH EUROPE`, `PHIL/INDO`, `AMERICAS NORTH`, `AMERICAS WEST`, `VIETNAM`, `AMERICAS EAST`, `RU HEAD OFFICE`, `DIRECT FACTORY`, `AMERICAS OEM`, `SE ASIA`, `OUT OF SE ASIA`, `P_EMEA`

**4. Order Types**
`SHIPMENT`, `BACKLOG`, `FATO`, `PAST DUE`, `BACKLOG - GIT`, `CROSSDOCK`, `PAST DUE - GIT`, `CONSIGNMENT`, `BOOKING`
 
**5. Focus Flags**
`Yes`, `No`

**6. Channels & Distributors**
- **`g7` (Distributor Name)**: `Non-G7`, `TTI`, `ARROW`, `AVNET`, `DIGIKEY`, `MOUSER`, `FUTURE`, `RUTRONIK`
- **`g7_flag` (Is Distributor)**: `Yes`, `No`

**7. Common Customers**
`JABIL`, `TTI`, `ARROW`, `FLEX`, `HON HAI`, `AVNET`, `CONTINENTAL`, `HOLDER`, `DELTA`, `SANMINA`, `DIGIKEY`, `MOUSER`, `CELESTICA`, `SUNLORD`, `NT SALES`, `CLWELL`, `QUANTA`, `FUTURE`, `JILITONG`, `WISTRON`, `RUTRONIK`, `SIEMENS`, `USI`, `PEGATRON`, `LUXSHARE`, `LITE-ON`, `FARNELL`, `MIKASA`, `ZF`, `APTIV`, `VISTEON`, `COMPAL`, `INVENTEC`, `WACHING`, `CORNDI`, `KING POWER`, `TSMT`, `SANSHIN`, `ANSON`, `LG`, `HUAWEI`, `BOSCH`, `HELLA`, `MARELLI`, `GENNEX`, `BENCHMARK`, `RYOSAN`, `REOTEC`, `AIAC`, `KAIFA`, `SAMSUNG`, `WINNER`, `SS-PARTS`, `VALEO`, `ELITEK`, `SATORI`, `ARTESYN`, `ARFA`, `NEW KINPO`, `VITESCO`, `RUIYI`, `ACBEL`, `GEMTEK`, `MITAC`, `GSK`, `RS GROUP`, `E.I.L.`, `ERICSSON`, `MELECS`, `ASKEY`, `BORGWARNER`, `SUNTRON`, `KIMBALL`, `WNC`, `GLORISON`, `ACCTON`, `LEAR`, `ALPHA-NET`, `MICRO-STAR`, `QISDA`, `ASCA`, `SAMPLES - EXPORT`, `BYD`, `SHINKO`, `PROTECH`, `PRIMAX`, `PHIHONG`, `SE SPEZIAL`, `WITTIG ELECTRONIC`, `WELLDONE`, `TRANSFER MULTISORT`, `YUCHENG`, `HARMAN`, `PROSPECT`, `KOSTAL`, `LETDO`, `WKK`, `ZTE`, `CHUANGSI`, `VITAL`

**8. Product Detail (pbu)**
`R-Chip`, `Ceramic`, `MLCC`, `POWER`, `TANTALUM`, `F&E`, `AMT`, `CPT`, `Telemecanique`, `Wired Comm`, `Wireless`, `Nexensos`, `MLCC PBU OEM (PLP)`, `Teapo`, `MLCC(KOE TYPE_2)`, `Wired Comm PBU OEM (PLP)`, `XSEMI`, `OTHERS`, `uPI`, `Wireless PBU OEM (PLP)`, `APEC`, `E-Cap`

**9. Product Detail (pbu_1)**
`COMMODITY`, `SPECIALTY`, `AUTOMOTIVE`, `Inductor - Std`, `HIGH CAP`, `FILM`, `MAGNETICS`, `POLYMER`, `MNO2`, `Network_Pulse`, `Power - Smart Power`, `CPC`, `LYTICS`, `Leaded-R`, `LIMIT SWITCHESES`, `Automotive - EGSTON`, `MCP`, `FERRITE`, `SUPERCAPS`, `Network_Bothhand`, `SENSORS & ACTUATORS`, `INDUCTIVE SENSORS`, `Wireless Infrastructure`, `SAFETY SWITCHES`, `PHOTOELECTRIC`, `Rebate`, `Wireless Consumer`, `LTCC Chilisin`, `Inductor - Power`, `T WIRED`, `OTHERS`, `PRESSURE SWITCHES`, `VTM`, `E-CAP`, `ACCESSORIES`

**10. Product Detail (pbu_2)**
`Automotive Commodity`, `RC0402`, `RC0603`, `CC0402`, `CC0603`, `RC0805`, `METAL`, `RC0201`, `RC1206`, `WW_Std`, `HCV X7R`, `RT`, `SMD_Std`, `AC`, `AS (Soft-Term)`, `Mold_L_Std`, `CC0805`, `CC0201`, `RLPT`, `Power`, `CM-MNO2 SMD`, `AC HC >=105`, `CM-KO SMD`, `HV >=500V`, `RFI FILM RADIAL`, `Ceramic`, `HC X5R`, `AC LINE FILTER`, `OPEN/FLOAT`, `YC`, `Comm 0603`, `CC >=1206`, `Mold_M_Std`, `Surge`, `Comm 0805`, `FERRITE`, `AC Commodity`, `PULSE`, `Comm 0402`

> [!IMPORTANT]
> **Resolution Protocol**:
> 1. **Check Synonyms**: If input matches "User Input" in Table A, apply "Correct SQL Logic".
> 2. **Check Valid Lists**: If input resembles a value in List B, map to that valid value.
> 3. **Search**: If it's a specific Customer or Product Sub-unit (pbu) not listed here, use `LIKE` across relevant columns (`customer_parent`, `pbu`, etc.).

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
- **Growth % Format**: Always report both Delta and Growth %.

### 4.3 Cross-Table Aggregation Patterns (Budget vs Billing / BB Ratios)
**SOTA CTE-First Protocol**: For ANY query involving multiple fact tables (e.g., Hit Rate, Book-to-Bill), you **MUST** follow this 5-step strict isolation pattern.

1.  **Isolation (CTE 1)**: Filter & Aggregate Table A (e.g., Billing) in its own CTE.
2.  **Isolation (CTE 2)**: Filter & Aggregate Table B (e.g., Budget) in its own CTE.
3.  **Robust Join**: Use `FULL OUTER JOIN` on common keys (e.g., `ru`, `customer_parent`, `year_month`).
    *   *Why?* captures "Sales without Budget" (Upside) and "Budget without Sales" (Zero Hit Rate).
4.  **Resolution (Coalesce)**:
    *   Dimensions: `COALESCE(b.ru, t.ru) as ru`
    *   Metrics: `COALESCE(b.total_sales, 0) as actuals`, `COALESCE(t.total_budget, 0) as budget`
5.  **Calculation**: Perform final division or ratio math in the outer SELECT.

**Standard Formulas (Apply Protocol Above)**:
- **BB Ratio (Value)**: `BookingTotalSales / NULLIF(BillingTotalSales, 0)`
- **BB Qty Ratio (Volume)**: `BookingTotalQty / NULLIF(BillingTotalQty, 0)`
- **Budget Achievement % (Hit Rate %)**: `BillingTotalSales / NULLIF(BudgetTotal, 0)`
    - *NOTE*: Use `order_type='SHIPMENT'` for Billing unless "OTR" Hit Rate is asked.
    - *NOTE*: Do NOT join on `order_type` for the Budget CTE.
    - *NOTE*: If filtering by Customer, apply `(customer_parent LIKE '%X%' OR local_assembler LIKE '%X%' OR final_customer LIKE '%X%')` to **BOTH** CTEs.

### 4.4 Time Period Rules & Proxies (CRITICAL)
**Granularity**: The data is **MONTHLY**. "Today", "Current", or "Latest" queries must align to the **Latest Closed Month**.

| Situation | REQUIRED SQL Pattern |
|-----------|---------------------|
| **Latest Closed Month** | `year_month = FORMAT(DATEADD(MONTH, -1, GETDATE()), 'yyyy-MM')` |
| **Specific Future Month** | **QUERY EXACTLY**: `year_month = 'YYYY-MM'` <br> **CRITICAL**: If user asks for '2025-04', you **MUST** query '2025-04'. **DO NOT** use the 'Latest Closed Month' proxy. It is better to return empty results than to proxy incorrectly. |
| **MTD (Month-to-Date)** | `WHERE year_month = FORMAT(DATEADD(MONTH, -1, GETDATE()), 'yyyy-MM')` (Proxy) |
| **QTD (Quarter-to-Date)** | `WHERE year_month >= FORMAT(DATEADD(quarter, DATEDIFF(quarter, 0, DATEADD(month, -1, GETDATE())), 0), 'yyyy-MM') AND year_month <= FORMAT(DATEADD(month, -1, GETDATE()), 'yyyy-MM')` |
| **YTD (Year-to-Date)** | `WHERE year_month >= FORMAT(DATEFROMPARTS(YEAR(DATEADD(month, -1, GETDATE())), 1, 1), 'yyyy-MM') AND year_month <= FORMAT(DATEADD(month, -1, GETDATE()), 'yyyy-MM')` |
| **"Last N months"** | `year_month >= FORMAT(DATEADD(MONTH, -(N+1), GETDATE()), 'yyyy-MM') AND year_month < FORMAT(GETDATE(), 'yyyy-MM')` |
| **Future / Risk Analysis** | Only apply logic if analyzing "Risk" or "Miss". If user asks for "Forecast" or "Budget" for future, query explicit future months. |

### 4.5 Mandatory Filter Standards
- **Sales / Revenue / Billing**: You **MUST** filter `order_type = 'SHIPMENT'` unless "OTR" (Order-To-Revenue) is explicitly requested.
    - *Rationale*: Non-shipment types (Backlog, etc.) are valid BILLING records but not realized REVENUE.
- **Backlog**: You **MUST** Query `ods.fact_monthly_sales_poa_billing` with `order_type <> 'SHIPMENT'`.
    - *Rationale*: Backlog is defined as "Billing records not yet shipped". **NEVER** use the Booking table for Backlog.
- **Booking**: Use `ods.fact_monthly_sales_poa_booking`.
    - *Note*: Booking table values are always valid (no `order_type` filter needed usually, but `order_type='BOOKING'` is safe).

**Example: Hit Rate Logic**
```sql
WITH CTE_Billing AS (
    SELECT customer_parent, SUM(total_sales) as sales
    FROM ods.fact_monthly_sales_poa_billing
    WHERE order_type = 'SHIPMENT' AND -- filters...
    GROUP BY customer_parent
),
CTE_Budget AS (
    SELECT customer_parent, SUM(total_budget) as budget
    FROM ods.fact_monthly_sales_poa_budget
    WHERE -- filters...
    GROUP BY customer_parent
)
SELECT
    COALESCE(b.customer_parent, t.customer_parent) as customer_parent,
    COALESCE(b.sales, 0) as actuals,
    COALESCE(t.budget, 0) as target,
    COALESCE(b.sales, 0) / NULLIF(COALESCE(t.budget, 0), 0) as hit_rate
FROM CTE_Billing b
FULL OUTER JOIN CTE_Budget t ON b.customer_parent = t.customer_parent
```

**Example: Hit Rate MoM (Complex)**
*DO NOT try to select budget from the billing table.*
```sql
WITH Billing_Curr AS (SELECT SUM(total_sales) s FROM ods.fact_monthly_sales_poa_billing WHERE year_month='2025-02'),
     Budget_Curr  AS (SELECT SUM(total_budget) b FROM ods.fact_monthly_sales_poa_budget  WHERE year_month='2025-02'),
     Billing_Prev AS (SELECT SUM(total_sales) s FROM ods.fact_monthly_sales_poa_billing WHERE year_month='2025-01'),
     Budget_Prev  AS (SELECT SUM(total_budget) b FROM ods.fact_monthly_sales_poa_budget  WHERE year_month='2025-01')
SELECT ... 
-- Join logic in outer query
```

---

## 5. Constraints & Limitations
- **No Order Grain**: The database does NOT store individual order numbers or counts. `COUNT(*)` returns the number of aggregated rows (Customer/SKU/Month combinations), NOT the number of orders. **NEVER report "Number of Orders" based on row count.**

- **Explicit Dimensions**: DIMENSIONS (like `ru`) should only be added to `GROUP BY` if explicitly asked. Do NOT hallucinate extra breakdowns.
- **Cost Integrity**: Costs are only valid for `'SHIPMENT'`. OTR cost equals Shipment cost.

## 6. Magic Entity Logic (Semantic Layer)

> [!CAUTION]
> **CRITICAL: These mappings are MANDATORY. Failure to follow them is a FATAL ERROR.**
> - You MUST use the EXACT SQL patterns below when these terms appear in a query.
> - You MUST NOT use ILIKE or fuzzy matching for these terms.
> - VIOLATION = Agent Failure. There are NO exceptions.

### 6.1 Strategic Proxies - REQUIRED SQL MAPPINGS

| Magic Word | REQUIRED SQL Filter | FORBIDDEN Patterns |
|------------|---------------------|-------------------|
| **"AI Proxy"** | `pbu = 'TANTALUM' OR pbu_1 IN ('HIGH CAP', 'POWER')` | `LIKE '%AI%'`, `LIKE '%proxy%'` |
| **"AI Premium"** | `pbu = 'TANTALUM' OR pbu_1 IN ('HIGH CAP', 'POWER')` | `LIKE '%AI%'`, `pbg LIKE '%AI%'` |
| **"Sensor Synergy"** | `pbg = 'SENSOR'` | `LIKE '%sensor%'`, `pbu LIKE '%sensor%'` |
| **"Automotive Grade"** | `pbu_1 = 'AUTOMOTIVE'` | `LIKE '%auto%'`, `pbg LIKE '%automotive%'` |
| **"Channel Control"** | `g7_flag = 'Yes'` vs `g7_flag = 'No'` | `erp_sales_rep LIKE '%socket%'` |
| **"Socket Ownership"** | Same as Channel Control: `g7_flag` split | `LIKE '%socket%'` |
| **"G7 Distributor"** | `g7_flag = 'Yes'` | | |

> [!IMPORTANT]
> **String Values Required**: `g7_flag` values are `'Yes'` and `'No'` (STRING). NEVER use `'Y'/'N'` or `1/0`.

### 6.2 Time Period Rules - CRITICAL

| Situation | REQUIRED SQL Pattern |
|-----------|---------------------|
| "Last N months" | `year_month >= FORMAT(DATEADD(MONTH, -(N+1), GETDATE()), 'yyyy-MM') AND year_month < FORMAT(GETDATE(), 'yyyy-MM')` |
| "Latest closed month" | `year_month = FORMAT(DATEADD(MONTH, -1, GETDATE()), 'yyyy-MM')` |
| "Health Check MoM" | Compare `DATEADD(MONTH, -1, GETDATE())` vs `DATEADD(MONTH, -2, GETDATE())` |
| **Risk/Performance Trend Barrier** | `year_month <= FORMAT(DATEADD(MONTH, -1, GETDATE()), 'yyyy-MM')` (NEVER check future budget misses) |


### 6.3 Risk Definitions
- **"Zombie Backlog"**: `order_type <> 'SHIPMENT' AND DATEDIFF(day, CAST(year_month + '-01' AS DATE), GETDATE()) > 90`. (Default: Group by **ru**).
  - *SQL Tip*: `year_month` is a string (YYYY-MM). You MUST cast it to DATE (append '-01') for `DATEDIFF`.
- **"Pas Due Risk" / "Broken Promises"**: `order_type = 'PAST DUE'` (Show top customers by value).
- **"Profit Dilution"**: Significant Month-over-Month decline in Gross Margin % (`gm_percent`).
- **"Pricing Power"**: Rising `ASP` trend alongside rising or stable `total_qty`.
- **"Focus Products" / "Focus Tracker"**: `focus_flag = 'Yes'`. (Strict String).
- **"Key Account Churn"**: Compare Current Month Sales vs Previous Month Sales per Customer. Order by biggest decline (Value).

