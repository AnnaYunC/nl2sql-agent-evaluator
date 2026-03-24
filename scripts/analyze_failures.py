import csv

input_file = (
    "c:\\Users\\Anna.YR.Chen\\Projects\\sales_agent\\data\\qa\\step4_final_20260203_100018.csv"
)
output_file = "c:\\Users\\Anna.YR.Chen\\Projects\\sales_agent\\data\\qa\\failures_analysis.txt"

fail_count = 0
failures = []

with open(input_file, mode="r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if row["evaluation_grade"] == "FAIL":
            fail_count += 1
            failures.append(
                {
                    "id": row.get("difficulty", "") + "_" + str(reader.line_num),
                    "question": row["question"],
                    "reason": row["evaluation_reason"],
                    "sql": row["generated_sql"],
                }
            )

with open(output_file, mode="w", encoding="utf-8") as outfile:
    outfile.write(f"Total FAIL count: {fail_count}\n\n")
    for f in failures:
        outfile.write(
            f"ID: {f['id']}\nQuestion: {f['question']}\nReason: {f['reason']}\nSQL Snippet: {f['sql'][:200]}...\n\n"
        )

print(f"Found {fail_count} failures. Written to {output_file}")
