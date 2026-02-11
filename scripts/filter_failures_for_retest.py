import csv
import sys

def filter_failures(input_csv, output_csv):
    """Filters rows where evaluation_grade is FAIL."""
    try:
        with open(input_csv, 'r', encoding='utf-8') as f_in:
            reader = csv.DictReader(f_in)
            rows = list(reader)
        
        failed_rows = [r for r in rows if r.get('evaluation_grade') == 'FAIL']
        
        if not failed_rows:
            print("No failures found to retest.")
            return

        print(f"Found {len(failed_rows)} failed queries. Saving to {output_csv}...")
        
        # We need to keep columns expected by Step 3. 
        # Step 3 expects: difficulty, question, metric, dimension, expected_answer
        # It largely preserves existing columns.
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(failed_rows)
            
        print("Done.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    input_file = r"c:\Users\Anna.YR.Chen\Projects\sales_agent\data\qa\step4_final_20260211_103145.csv"
    output_file = r"c:\Users\Anna.YR.Chen\Projects\sales_agent\data\qa\retest_input.csv"
    filter_failures(input_file, output_file)
