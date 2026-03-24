"""Step 4: Result Evaluation logic."""

import json


def evaluate(client_openai, model, level, question, expected, actual):
    # Overall weight: 80% SQL correctness (meaning), 20% Response format/semantics
    BASE_RULES = (
        "EVALUATION WEIGHTING:\n"
        "1. 80% SQL CORRECTNESS: Focus on SQL intent and meaning. It does NOT need to be identical to Ground Truth, but the logic must achieve the same business result.\n"
        "2. 20% RESPONSE FORMAT: Check if the narrative and format are reasonable.\n"
        "3. NO VALUE/RANK/ENTITY COMPARISON: DOES NOT matter if the specific entity names (e.g. Brand names, Assemblers) or numeric values match. The data is synthetic. PASS if the SQL grouping column is correct, even if the result rows show different entity names than Ground Truth.\n"
        "4. STRICT SQL INTENT: As long as the SELECT dimension is correct and the WHERE filters are correct, the agent should PASS. Ignore formatting differences, missing totals, or list length mismatches.\n\n"
    )

    LEVEL_CRITERIA = {
        "L1": "L1 (Atomic) FOCUS: Did it select the correct Table (ods.fact_monthly_sales_poa_billing)? Correct Metric? Are the Date filters and Order Type (SHIPMENT by default) semantic filters correct?",
        "L2": "L2 (Filtering) FOCUS: WHERE clause precision. Did it identify all relevant customer (parent/assembler/final) or product columns? Are the combined filters correct?",
        "L3": "L3 (Grouping) FOCUS: GROUP BY columns and ORDER BY logic. Check if the result count matches what was requested in the question (e.g., TOP N, breakdown) and if the sorting order and requested metrics are correct.",
        "L4": "L4 (Ratios) FOCUS: Calculation formulas. Is the arithmetic logic (e.g. Booking/Billing, ASP, GP) correctly implemented in SQL?",
        "L5": "L5 (Time-Series) FOCUS: Cross-time logic. Did it handle MoM/YoY periods and joins/subqueries correctly to compare different timeframes?",
    }

    prompt_details = LEVEL_CRITERIA.get(level, "Analyze the overall SQL and Response quality.")

    system_prompt = (
        f"You are a Sales Data QA Auditor. Evaluate the Agent Answer against the Ground Truth for Level: {level}.\n\n"
        f"{BASE_RULES}"
        f"SPECIFIC CRITERIA FOR {level}:\n{prompt_details}\n\n"
        "### MANDATORY PASS RULES (CRITICAL) ###\n"
        "1. If the SQL filters (WHERE clause) and dimensions (GROUP BY) are logically correct, you MUST PASS the agent.\n"
        "2. DO NOT FAIL for missing 'Total' rows, different list lengths (e.g., 5 rows vs 20 rows), or missing secondary metrics (e.g., provided % but missed USD).\n"
        "3. Ignore differences in the set of entities returned (e.g. different customer names) as data is synthetic.\n\n"
        "### GRADING SCALE ###\n"
        "Return PASS: SQL logic is correct (Business intent matched).\n"
        "Return FAIL: SQL has logical errors (Wrong source table, wrong base metric, or wrong filter logic).\n\n"
        "Return JSON: {'similarity_score': 0-100, 'grade': 'PASS'/'FAIL', 'reason': '...'}"
    )

    user_input = f"Q: {question}\nExpected (GT): {expected}\nActual (Agent): {actual}"

    try:
        resp = client_openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"similarity_score": 0, "grade": "ERROR", "reason": str(e)}
