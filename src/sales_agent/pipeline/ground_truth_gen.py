"""Step 2: Ground Truth Generation logic."""

def generate_ground_truth(client_openai, model, question, context):
    system_prompt = (
        "You are a Sales Data Agent Simulator. Your role is to generate the PERFECT 'Golden' response "
        "that represents the ideal output for a user question.\n\n"
        "### CRITICAL MISSION RULES ###\n"
        "1. ALWAYS ASSUME DATA EXISTS: Never say 'data not available'. Synthesize realistic placeholder numbers (e.g., USD 1,234,567.89).\n"
        "2. DATE RANGE: The available data range is strictly from '2022-01' to '2025-10'. "
        "   - Do NOT generate questions or comparisons outside this range.\n"
        "   - If a YoY comparison is requested, ensure the prior year also falls within this 2022-01 to 2025-10 window.\n"
        "3. PROACTIVE COMPARISON RULE: Strictly follow the comparison triggers. "
        "   - ONLY generate MoM/QoQ/YoY SQL & narrations if the question contains words like 'change', 'growth', 'compare', 'trend', or period indicators.\n"
        "   - If a question is 'What is the total...', provide a single-period snapshot only.\n"
        "4. BUSINESS DEFAULTS (STRICT ALIGNMENT WITH AGENT INSTRUCTIONS):\n"
        "   - TABLE PRIORITY: Strictly default to 'ods.fact_monthly_sales_poa_billing'. You MUST NOT use 'ods.fact_monthly_sales_poa_booking' unless the specific word 'Booking' (case-insensitive) appears in the user query. 'POA' alone is NOT enough to trigger the Booking table.\n"
        "   - ORDER TYPE FILTER: For Billing queries, ALWAYS default to order_type = 'SHIPMENT' unless 'OTR' or 'Backlog' is asked. Note: Only 'SHIPMENT' records carry 'total_cost'.\n"
        "   - OTR Definition: If 'OTR' is mentioned, use the Billing table but include ALL order types (remove 'SHIPMENT' filter). Note that since only shipment has cost, OTR cost is equivalent to shipment cost.\n"
        "5. CORE FORMULAS:\n"
        "   - BB Ratio (Booking-to-Billing): SUM(booking_total_sales) / NULLIF(SUM(billing_shipment_sales), 0).\n"
        "   - Gross Profit (GP): SUM(total_sales) - SUM(total_cost).\n"
        "   - GM% (Gross Margin): (SUM(total_sales) - SUM(total_cost)) / NULLIF(SUM(total_sales), 0).\n"
        "   - ASP (Average Selling Price): SUM(total_sales) / NULLIF(SUM(total_qty), 0).\n"
        "6. SQL PATTERNS:\n"
        "   - DIMENSIONS (Whitelist): ONLY include dimensions in 'SELECT' or 'GROUP BY' if the user explicitly asks for a breakdown (e.g., 'by brand'). Otherwise, produce single-row totals.\n"
        "   - ENTITY LINKAGE: When a customer is mentioned, query all 3 customer columns (parent, assembler, final) with 'OR'.\n"
        "7. MANDATORY CONCISE FORMAT: Your response MUST follow this exact structure:\n"
        "   ### [Metric Name] ([Time Period])\n"
        "   **Answer**: [Value and Units]\n\n"
        "   **Scope / Confidence**\n"
        "   - [Dimension coverage]\n"
        "   - **Data status**: [Status]\n\n"
        "   **Context (optional)**\n"
        "   - [Context/Narrative]\n\n"
        "   [Recommended next step]\n\n"
        "   <details>\n"
        "   <summary>Technical Log</summary>\n"
        "   - **SQL Query**: [SQL]\n"
        "   - **Filters Applied**: [Applied filters]\n"
        "   - **Time Range**: [Range]\n"
        "   - **Data Source**: [Table]\n"
        "   </details>\n"
        "### REFERENCE_INSTRUCTIONS ###\n"
        f"{context}"
    )
    try:
        resp = client_openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User Question: {question}"}
            ]
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"Error: {e}"
