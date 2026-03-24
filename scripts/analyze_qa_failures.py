import csv
import json

csv_path = r"c:\Users\Anna.YR.Chen\Projects\sales_agent\data\qa\step4_final_20260209_130446.csv"


def analyze_failures():
    failed_cases = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("evaluation_grade") == "FAIL":
                    failed_cases.append(
                        {
                            "question": row.get("question"),
                            "sql": row.get("generated_sql"),
                            "reason": row.get("evaluation_reason"),
                            "expected": row.get("expected_answer"),
                        }
                    )

        output_path = r"c:\Users\Anna.YR.Chen\Projects\sales_agent\data\qa\failures_analysis.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(failed_cases, f, indent=2, ensure_ascii=False)

        print(f"Saved {len(failed_cases)} failures to {output_path}")

    except Exception as e:
        print(f"Error reading CSV: {e}")


if __name__ == "__main__":
    analyze_failures()
