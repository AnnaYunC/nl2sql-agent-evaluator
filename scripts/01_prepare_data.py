"""
Utility to fetch distinct sample values from Fabric SQL Endpoint tables.

Inputs:
    - .env (FABRIC_SQL_ENDPOINT)
Outputs:
    - data/sample/sample_data_billing.txt
    - data/sample/sample_data_booking.txt
    - data/sample/sample_data_budget.txt
"""

import os
import pyodbc
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_sample_data(table_name, columns, output_file):
    print(f"Processing table: {table_name}")
    
    endpoint = os.getenv("FABRIC_SQL_ENDPOINT")
    if not endpoint:
        print("❌ Error: FABRIC_SQL_ENDPOINT not found in .env")
        return

    # Connection string for Fabric Warehouse using MSI or Interactive Browser
    # Note: InteractiveBrowserCredential is handled by the driver when Authentication=ActiveDirectoryInteractive
    conn_str = (
        f"Driver={{ODBC Driver 17 for SQL Server}};"
        f"Server={endpoint};"
        f"Database=DATAAGENT_WH;"
        f"Authentication=ActiveDirectoryInteractive;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        
        # We only need a sample or top records to get distinct values, 
        # but to be safe and efficient, we query 10 distinct values per column directly if possible,
        # or just pull a reasonable amount of data and process in pandas.
        # Since we want to be sure about the 10 distinct values, pulling a subset is better.
        
        output_lines = []
        metric_cols = ["total_sales", "total_qty", "total_cost", "total_budget"]
        
        for col in columns:
            try:
                # Decide strategy based on column type
                if col in metric_cols:
                    # For metrics/dates, just take distinct values from a sample
                    query = f"SELECT TOP 50 [{col}] FROM {table_name}"
                    df = pd.read_sql(query, conn)
                    values = df[col].dropna().unique().astype(str).tolist()
                    # Take random sample of 30
                    sample_values = pd.Series(values).sample(n=min(30, len(values)), random_state=42).tolist() if values else []
                    
                else:
                    # For dimensions, get Top 100 by frequency
                    query = f"SELECT TOP 50 [{col}], COUNT(*) as cnt FROM {table_name} WHERE [{col}] IS NOT NULL GROUP BY [{col}] ORDER BY cnt DESC"
                    print(f"   Fetching Top 50 for: {col}")
                    df = pd.read_sql(query, conn)
                    sample_values = df[col].astype(str).tolist()

                if sample_values:
                    output_lines.append(f"{col}: {', '.join(sample_values)}")
                else:
                    output_lines.append(f"{col}: [No data]")
                    
            except Exception as col_error:
                print(f"   Error fetching {col}: {col_error}")
                output_lines.append(f"{col}: [Error]")
        
        conn.close()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        
        print(f"Sample data saved to {output_file}")

    except Exception as e:
        print(f"Error processing {table_name}: {e}")

def main():
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    sample_data_dir = os.path.join(project_root, "data", "sample")
    os.makedirs(sample_data_dir, exist_ok=True)

    billing_columns = ["year_month","order_type","ru","sub_unit","pbg","pbu","pbu_1","pbu_2","focus_flag","customer_parent","local_assembler","final_customer","g7","fu_us_oem_flag","fu_global_ems_flag","g7_flag","fu_emea_oem_flag","erp_sales_rep","total_sales","total_cost","total_qty","updated_date"]
    booking_columns = ["year_month","order_type","ru","sub_unit","pbg","pbu","pbu_1","pbu_2","focus_flag","customer_parent","local_assembler","final_customer","g7","fu_us_oem_flag","fu_global_ems_flag","g7_flag","fu_emea_oem_flag","erp_sales_rep","total_sales","total_qty","updated_date"]
    budget_columns = ["year_month","order_type","ru","sub_unit_cbr","pbg","pbu","pbu_1","pbu_2","focus_flag","customer_parent","local_assembler","final_customer","g7","fu_us_oem_flag","fu_global_ems_flag","g7_flag","fu_emea_oem_flag","total_budget","updated_date"]

    get_sample_data("ods.fact_monthly_sales_poa_billing", billing_columns, os.path.join(sample_data_dir, "sample_data_billing.txt"))
    get_sample_data("ods.fact_monthly_sales_poa_booking", booking_columns, os.path.join(sample_data_dir, "sample_data_booking.txt"))
    get_sample_data("ods.fact_monthly_sales_poa_budget", budget_columns, os.path.join(sample_data_dir, "sample_data_budget.txt"))

if __name__ == "__main__":
    main()
