import argparse
import csv


def analyze_qa_results(input_file):
    passed_count = 0
    failed_count = 0
    failures = []

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            total_cases = 0
            for row in reader:
                total_cases += 1
                grade = row.get("evaluation_grade", "").upper()
                if grade == "PASS":
                    passed_count += 1
                elif grade == "FAIL":
                    failed_count += 1
                    failures.append(
                        {
                            "id": f"{row.get('difficulty', 'N/A')}_{total_cases}",
                            "difficulty": row.get("difficulty", "N/A"),
                            "question": row.get("question", ""),
                            "reason": row.get("evaluation_reason", ""),
                            "generated_sql": row.get("generated_sql", ""),
                        }
                    )

        pass_rate = (passed_count / total_cases * 100) if total_cases > 0 else 0

        print(f"Total Cases: {total_cases}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")
        print(f"Pass Rate: {pass_rate:.2f}%")
        print("\nFailures:")
        for fail in failures:
            print(f"[{fail['difficulty']}] {fail['question']}")
            print(f"Reason: {fail['reason']}")
            # print(f"SQL: {fail['generated_sql'][:100]}...") # Optional: print SQL snippets
            print("-" * 20)

    except FileNotFoundError:
        print(f"Error: File not found: {input_file}")
    except Exception as e:
        print(f"Error parsing file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze QA Results CSV")
    parser.add_argument("input_file", help="Path to the QA results CSV file")
    args = parser.parse_args()

    analyze_qa_results(args.input_file)
