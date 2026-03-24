"""Step 3: Agent Execution logic."""

import json


def run_agent(fabric_client, question):
    try:
        details = fabric_client.get_run_details(question)
        return {
            "answer": details.get("answer", ""),
            "sql": json.dumps(details.get("sql_analysis", {}).get("sql_queries", [])),
        }
    except Exception as e:
        return {"answer": f"Error: {e}", "sql": "[]"}
