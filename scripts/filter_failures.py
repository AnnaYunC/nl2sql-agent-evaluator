import csv
import os

fin_path = r"c:\Users\Anna.YR.Chen\Projects\sales_agent\data\qa\step4_final_20260206_140525.csv"
fout_path = r"c:\Users\Anna.YR.Chen\Projects\sales_agent\data\qa\retest_failures.csv"

if not os.path.exists(fin_path):
    print(f"Error: {fin_path} does not exist.")
    exit(1)

with (
    open(fin_path, "r", encoding="utf-8") as fin,
    open(fout_path, "w", newline="", encoding="utf-8") as fout,
):
    reader = csv.DictReader(fin)
    # We only need specific columns for Step 3 input (it behaves like Step 2 output/Step 3 input)
    # Step 3 expects: difficulty, question, metric, dimension, expected_answer
    fieldnames = ["difficulty", "question", "metric", "dimension", "expected_answer"]

    writer = csv.DictWriter(fout, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()

    count = 0
    for row in reader:
        if row.get("evaluation_grade") != "PASS":
            # Create a new dict with only the required fields
            new_row = {k: row[k] for k in fieldnames}
            writer.writerow(new_row)
            count += 1

    print(f"Successfully wrote {count} failed rows to {fout_path}")
