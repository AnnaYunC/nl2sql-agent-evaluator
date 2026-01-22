import os
import csv
import json
import time
import sys
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Add project root to sys.path to allow importing from src
# Since main.py is in root, we just add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.fabric_data_agent_client import FabricDataAgentClient, TerminalLogger

# Load environment variables
load_dotenv()

def generate_ground_truth(client: OpenAI, user_prompt: str, context: str) -> str:
    """
    Step 1: Use OpenAI to generate an 'expected' correct answer based on context.
    """
    model = os.getenv("LLM_MODEL", "gpt-5-nano")
    system_prompt = (
        "You are an expert Sales Data Analyst. Given the following data schema and business rules, "
        "predict what the correct answer to the user's query should be. "
        "Your prediction should focus on the analysis dimensions and filtering rules."
    )
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nUser Query: {user_prompt}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ground truth generation failed: {e}"

def evaluate_answer(client: OpenAI, user_prompt: str, expected_answer: str, agent_answer: str) -> Dict:
    """
    Step 3: Compare results.
    """
    model = os.getenv("LLM_MODEL", "gpt-5-nano")
    system_prompt = (
        "You are a Quality Assurance specialist. Compare the 'Agent Answer' against the 'Expected Ground Truth'. "
        "Your primary goal is to verify if the agent correctly identified the: "
        "1. Analysis Dimensions (e.g., grouping by brand, RU, or time). "
        "2. Filtering Conditions (e.g., specific year_month, focus_flag, or G7 status). "
        "Ignore minor wording differences. If the dimensions and filters are correct, give a high similarity score and PASS. "
        "Return JSON: {'similarity_score': 0-100, 'grade': 'PASS'/'FAIL', 'reason': '...'}"
    )
    
    user_prompt_eval = f"Query: {user_prompt}\nGround Truth: {expected_answer}\nAgent Answer: {agent_answer}"
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt_eval}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"similarity_score": 0, "grade": "ERROR", "reason": str(e)}

def read_file(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def execute_pipeline():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(root_dir, "docs", "process")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"log_{timestamp}.txt")
    sys.stdout = TerminalLogger(log_path)
    
    print(f"📝 Execution log started at {datetime.now()}")

    # Paths (re-calculate to be absolute)
    instr_dir = os.path.join(root_dir, "docs", "da_instructions")
    sample_dir = os.path.join(root_dir, "scripts")
    
    # Load Context for Step 1
    print("📖 Loading context for Ground Truth generation...")
    context = (
        f"Agent Instructions:\n{read_file(os.path.join(instr_dir, 'da_agent_instruction.md'))}\n\n"
        f"Data Source Instructions:\n{read_file(os.path.join(instr_dir, 'da_data_source_instruction.md'))}\n\n"
        f"Billing Samples:\n{read_file(os.path.join(sample_dir, 'sample_data_billing.txt'))}\n\n"
        f"Booking Samples:\n{read_file(os.path.join(sample_dir, 'sample_data_booking.txt'))}"
    )

    # Configuration
    tenant_id = os.getenv("TENANT_ID")
    data_agent_url = os.getenv("DATA_AGENT_URL")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL")
    
    fabric_client = FabricDataAgentClient(tenant_id=tenant_id, data_agent_url=data_agent_url)
    openai_client = OpenAI(api_key=openai_api_key, base_url=openai_base_url)

    input_file = os.path.join(root_dir, "docs", "test_case", "test_case.csv")
    results_dir = os.path.join(root_dir, "docs", "test_results")
    os.makedirs(results_dir, exist_ok=True)
    output_file = os.path.join(results_dir, f"test_results_{timestamp}.csv")
    
    if not os.path.exists(input_file):
        print(f"❌ Input file {input_file} not found.")
        return

    test_cases = []
    with open(input_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_cases.append(row)

    print(f"📋 Found {len(test_cases)} test cases. Starting 3-Step Execution...")

    results = []
    for i, tc in enumerate(test_cases):
        prompt = tc.get("user_prompt") or tc.get("question")
        if not prompt: continue
        
        print(f"\n[{i+1}/{len(test_cases)}] Query: {prompt[:100]}")
        
        try:
            # Step 1: Generate Ground Truth
            print("🤖 Step 1: Generating Ground Truth via OpenAI...")
            ground_truth = generate_ground_truth(openai_client, prompt, context)
            
            # Step 2: Run Data Agent
            print("🚀 Step 2: Running Data Agent...")
            run_details = fabric_client.get_run_details(prompt)
            agent_answer = run_details.get("answer", "")
            sql_analysis = run_details.get("sql_analysis", {})
            
            # Debug output
            print(f"🐛 Agent Answer: {agent_answer}")
            print(f"🐛 SQL Analysis: {json.dumps(sql_analysis, indent=2)}")

            actual_sql = json.dumps(sql_analysis.get("sql_queries", []), indent=2)

            # Debug: Save full run details for the first case to analyze the technical error
            if i == 0:
                debug_file = "debug_run_details.json"
                with open(debug_file, "w", encoding="utf-8") as f:
                    json.dump(run_details, f, indent=2, default=str)
                print(f"🐛 Saved full run details to {debug_file}")
            
            # Step 3: Evaluate
            print("🧐 Step 3: Evaluating Similarity...")
            eval_result = evaluate_answer(openai_client, prompt, ground_truth, agent_answer)
            
            results.append({
                "user_prompt": prompt,
                "expected_answer": ground_truth,
                "agent_answer": agent_answer,
                "generated_sql": actual_sql,
                "similarity_score": eval_result.get("similarity_score"),
                "evaluation_grade": eval_result.get("grade"),
                "evaluation_reason": eval_result.get("reason")
            })
            print(f"✨ Score: {eval_result.get('similarity_score')} | Grade: {eval_result.get('grade')}")

        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({"user_prompt": prompt, "agent_answer": f"ERROR: {e}", "evaluation_grade": "ERROR"})

    # Save Results
    fieldnames = ["user_prompt", "expected_answer", "agent_answer", "generated_sql", "similarity_score", "evaluation_grade", "evaluation_reason"]
    with open(output_file, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"✅ Completed. Results saved to {output_file}")

if __name__ == "__main__":
    execute_pipeline()
