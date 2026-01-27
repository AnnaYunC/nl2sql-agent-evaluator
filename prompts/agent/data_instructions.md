# 1. Table Descriptions
- All tables provide monthly aggregated data.

# 2. Table Selection Rules
#### Use fact_monthly_sales_poa_billing when the question refers to:
- Actual sales / revenue
- Billed amounts
- Past-due shipments, consignment, GIT
- Historical performance
- Margin or cost

#### Use fact_monthly_sales_poa_booking when the question refers to:
- Bookings / orders received
- Pipeline / demand forecast
- Order intake analysis
- Pre-shipment status

If the user explicitly says "billing", "actual sales", or “booking”, choose accordingly.
If ambiguous:
- Prefer billing for financial performance
- Prefer booking for demand outlook

# 3. Common Dimensions and How to Interpret Them
#### 3.1 Time
- year_month: Always YYYY-MM. Use as main time filter.

If a user asks about “2025 August”, convert to '2025-08'.

#### 3.2 Order Type (Transaction Type)
- Billing: SHIPMENT,BACKLOG,BACKLOG - GIT,CONSIGNMENT,CROSSDOCK,FATO,PAST DUE,PAST DUE - GIT
- Booking: BOOKING

If the user references shipment status → billing table only.

#### 3.3 Region / Unit
- ru: Reporting Unit, a high-level region.
- sub_unit: Sub-regional or operating unit.

If a user names a country (e.g., Japan), map to related sub_unit only if explicitly mentioned.

#### 3.4 Brand and Product Type
- brand: product brand
- pbg: Product Business Group, a top level product type
- pbu: Product Business Unit, a sub-type under pbg
- pbu_1: lower-level of pbu
- pbu_2: lower-level of pbu_1
- focus_flag: yes/no flag, yes means the product is the focus product

The product hierarchy: pbg → pbu → pbu_1 → pbu_2.

#### 3.5 Customer Type
- customer_parent: top-level customer type, customer receiving the invoice.
- local_assembler: production or assembly customer
- final_customer: end customer who uses the final product.

The customer hierarchy: customer_parent → local_assembler → final_customer.
If a question mentions specific customer names, match them exactly.

#### 3.6 Channel and Flags
- g7: Channel classification.
- fu_us_oem_flag, fu_global_ems_flag, fu_g7_flag, fu_emea_oem_flag: yes/no flags.

Use these when user asks about OEM/EMS/G7 performance.

#### 3.7 Sales Rep
- erp_sales_rep: sales representative assigned in the ERP system

# 4. Metrics & Mandatory Output
#### Billing Table (ods.fact_monthly_sales_poa_billing)
- total_sales — total sales amount
- total_qty — total quantity sold
- total_cost — total cost incurred
- updated_date — data last updated date (**Mandatory in output**)

#### Booking Table (ods.fact_monthly_sales_poa_booking)
- total_sales — total undeliver sales amount (Booking Value). **DEFAULT for "Bookings", "Booking sales", or "Order received"**.
- total_qty — total quantity sold (Booking Volume). Use ONLY if "quantity", "qty", or "volume" is mentioned.
- updated_date — data last updated date (**Mandatory in output**)

#### General Rules & Limitations
- **Monthly Aggregated Data**: All metrics are aggregated by month.
- **Unsupported Metrics**: The data does **NOT** contain individual order numbers. Therefore, **Order Count**, **Number of Orders**, and **Average Sale per Order** cannot be calculated.
- If a user asks for "average sale per order", explain that we only have monthly totals and cannot see individual orders due to lack of `order_count`.
#### Common Formula Definitions
- **Gross Profit (GP)**: `SUM(total_sales) - SUM(total_cost)`
- **Gross Margin % (GM%)**: `(SUM(total_sales) - SUM(total_cost)) / NULLIF(SUM(total_sales), 0) * 100`
- **Average Selling Price (ASP)**: `SUM(total_sales) / NULLIF(SUM(total_qty), 0)`
- **Aggregation Note**: Always apply `SUM()` to base metrics before performing division or subtraction to ensure correct weighted averages across multiple dimensions.

- Use same dimensions for both tables.
- **Missing Data**: If data is not in the sample, provide a template record with NULL placeholders and explain the methodology.
