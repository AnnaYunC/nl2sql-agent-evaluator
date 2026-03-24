import csv


def analyze_failures(file_path):
    failures = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                if row.get("evaluation_grade") != "PASS":
                    failures.append(
                        {
                            "id": i,
                            "question": row.get("question"),
                            "grade": row.get("evaluation_grade"),
                            "reason": row.get("evaluation_reason"),
                            "agent_answer": row.get("agent_answer")[:200] + "..."
                            if row.get("agent_answer")
                            else "N/A",
                            "sql": row.get("generated_sql"),
                        }
                    )
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    with open("data/qa/failures_summary.txt", "w", encoding="utf-8") as outfile:
        outfile.write(f"Found {len(failures)} failures out of {i} rows.\n")
        outfile.write("-" * 50 + "\n")
        for fail in failures:
            outfile.write(f"Row {fail['id']} [{fail['grade']}]\n")
            outfile.write(f"Q: {fail['question']}\n")
            outfile.write(f"Reason: {fail['reason']}\n")
            outfile.write(f"Agent Answer Snippet: {fail['agent_answer']}\n")
            outfile.write(f"SQL Snippet: {fail['sql']}\n")
            outfile.write("-" * 50 + "\n")
    print("Analysis saved to data/qa/failures_summary.txt")


if __name__ == "__main__":
    analyze_failures(
        r"c:\Users\Anna.YR.Chen\Projects\sales_agent\data\qa\step4_final_20260206_163210.csv"
    )
