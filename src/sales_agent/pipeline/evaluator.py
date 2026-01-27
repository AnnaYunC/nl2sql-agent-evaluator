"""Step 4: Result Evaluation logic."""
import json

def evaluate(client_openai, model, question, expected, actual):
    system_prompt = (
        "Compare Agent Answer against Ground Truth. Focus on SQL logic, Dimensions, and Filters.\n"
        "EXPECTED FORMAT: Concise Executive Format with a collapsible Technical Log using <details>/<summary> tags.\n"
        "1. BUSINESS LOGIC: BB Ratio = Booking / Billing (Shipment). ASP = Sales / Qty. GP = Sales - Cost.\n"
        "2. CRITICAL: Do NOT compare numeric values (e.g., USD amounts, units). Numeric mismatches are EXPECTED due to synthetic data.\n"
        "3. LOGIC GAP: If the Agent provides a correct SQL query and filters but the summary text differs slightly in narrative, focus on the SQL correctness.\n"
        "Return JSON: {'similarity_score': 0-100, 'grade': 'PASS'/'FAIL', 'reason': '...'}"
    )
    user_input = f"Q: {question}\nExpected: {expected}\nActual: {actual}"
    try:
        resp = client_openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"similarity_score": 0, "grade": "ERROR", "reason": str(e)}
