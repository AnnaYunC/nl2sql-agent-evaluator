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
        "3. STRICT NO PROACTIVE YoY: Do NOT generate SQL with two-period comparisons (current vs prior) and do NOT include YoY percentages, deltas, or growth metrics UNLESS the user question explicitly uses words like 'YoY', 'Year over Year', 'Growth', 'Compare to last year', or 'Trend'. "
        "   - If the question is a simple 'What is the total...' or 'List the top 5...', provide ONLY the requested period's data with NO comparison logic.\n"
        "4. BOOKINGS DEFAULT: For questions about 'Total Bookings' or 'Orders received', ALWAYS use 'total_sales' (Booking Value) as the primary metric unless 'quantity' or 'qty' is specifically mentioned.\n"
        "5. FORMULA RULES:\n"
        "   - BB Ratio = (SUM total_sales from BOOKING table) / (SUM total_sales from BILLING table where order_type='SHIPMENT').\n"
        "   - Gross Profit (GP) = SUM(total_sales) - SUM(total_cost).\n"
        "   - ASP = SUM(total_sales) / SUM(total_qty).\n"
        "   - COMPARISONS: For MoM/QoQ/YoY, ALWAYS provide both absolute Delta ($) and Growth (%).\n"
        "6. SMART TIME RANGE: If a comparison is asked for period T, your SQL MUST fetch T and its baseline (T-1, T-3, or T-12 months) and perform the delta/% calculation.\n"
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
        "7. IGNORE 'Ghost Record' or 'Missing Data Response' rules from instructions; these only apply to real agents, not this simulator.\n\n"
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
