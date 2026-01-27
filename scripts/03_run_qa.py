import os
import sys
import csv
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from sales_agent.core.client import FabricDataAgentClient
from sales_agent.utils.logger import TerminalLogger
from sales_agent.pipeline import (
    question_gen,
    ground_truth_gen,
    executor,
    evaluator
)

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Sales Agent Testing Pipeline")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4], help="Run specific step only")
    parser.add_argument("--level", type=str, nargs="+", choices=["L1", "L2", "L3", "L4", "L5"], help="Level(s) to generate (for step 1)")
    parser.add_argument("--count", type=int, default=2, help="Number of questions to generate per level (for step 1)")
    parser.add_argument("--input", type=str, help="Input CSV (for steps > 1)")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("data/qa", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    sys.stdout = TerminalLogger(f"logs/pipeline_{timestamp}.log")
    
    openai_client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )
    model = os.getenv("LLM_MODEL", "gpt-5-nano")
    
    # Step 1: Question Generation
    if not args.step or args.step == 1:
        print("Step 1: Generating Questions...")
        
        # Load configuration from JSON
        config_path = "data/qa/generation_config.json"
        if not os.path.exists(config_path):
            print(f"Error: Config file {config_path} not found.")
            return
            
        with open(config_path, "r", encoding="utf-8") as f:
            gen_config = json.load(f)
            
        metrics = gen_config.get("metrics", [])
        dimensions = gen_config.get("dimensions", {})
        
        schema = ""
        with open("prompts/agent/data_instructions.md", "r", encoding="utf-8") as f:
            schema = f.read()
        
        questions = question_gen.generate_questions(
            openai_client, model, schema, "prompts/qa", metrics, dimensions, target_level=args.level, count=args.count
        )
        output = f"data/qa/step1_questions_{timestamp}.csv"
        with open(output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["difficulty", "question", "metric", "dimension"], quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(questions)
        print(f"Step 1 Completed. Questions saved to {output}")
        if args.step == 1: return
        args.input = output

    # Step 2: Ground Truth
    if not args.step or args.step == 2:
        print("Step 2: Generating Ground Truth...")
        rows = []
        input_csv = args.input or "data/qa/step1_questions.csv"
        if not os.path.exists(input_csv):
            # Try to find the latest step 1 file if no direct input
            import glob
            files = sorted(glob.glob("data/qa/step1_questions_*.csv"), reverse=True)
            if files: input_csv = files[0]
            else:
                print(f"Error: Step 1 output not found. Please run Step 1 or provide --input.")
                return

        with open(input_csv, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        
        # Load instructions as context
        agent_instr = ""
        data_instr = ""
        with open("prompts/agent/agent_instructions.md", "r", encoding="utf-8") as f:
            agent_instr = f.read()
        with open("prompts/agent/data_instructions.md", "r", encoding="utf-8") as f:
            data_instr = f.read()
            
        context = f"AGENT_INSTRUCTIONS:\n{agent_instr}\n\nDATA_SCHEMA:\n{data_instr}"
        
        for r in rows:
            print(f"Generating GT for: {r['question'][:50]}...")
            r["expected_answer"] = ground_truth_gen.generate_ground_truth(openai_client, model, r["question"], context)
        
        output = f"data/qa/step2_truth_{timestamp}.csv"
        with open(output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Step 2 Completed. Ground truth saved to {output}")
        if args.step == 2: return
        args.input = output

    # Step 3: Execution
    if not args.step or args.step == 3:
        print("Step 3: Running Agent...")
        rows = []
        input_csv = args.input or "data/qa/step2_truth.csv"
        if not os.path.exists(input_csv):
            import glob
            files = sorted(glob.glob("data/qa/step2_truth_*.csv"), reverse=True)
            if files: input_csv = files[0]
            else:
                print(f"Error: Step 2 output not found. Please run Step 2 or provide --input.")
                return

        with open(input_csv, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        
        fabric = FabricDataAgentClient(os.getenv("TENANT_ID"), os.getenv("DATA_AGENT_URL"))
        total = len(rows)
        for i, r in enumerate(rows, 1):
            print(f"[{i}/{total}] Running Agent for question: {r['question'][:60]}...")
            res = executor.run_agent(fabric, r["question"])
            r["agent_answer"] = res["answer"]
            r["generated_sql"] = res["sql"]
            
        output = f"data/qa/step3_results_{timestamp}.csv"
        with open(output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Execution results saved to {output}")
        if args.step == 3: return
        args.input = output

    # Step 4: Evaluation
    if not args.step or args.step == 4:
        print("Step 4: Evaluating...")
        rows = []
        input_csv = args.input or "data/qa/step3_results.csv"
        if not os.path.exists(input_csv):
            import glob
            files = sorted(glob.glob("data/qa/step3_results_*.csv"), reverse=True)
            if files: input_csv = files[0]
            else:
                print(f"Error: Step 3 output not found. Please run Step 3 or provide --input.")
                return

        with open(input_csv, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        
        total = len(rows)
        for i, r in enumerate(rows, 1):
            print(f"[{i}/{total}] Evaluating: {r['question'][:60]}...")
            res = evaluator.evaluate(openai_client, model, r["question"], r["expected_answer"], r["agent_answer"])
            r.update({
                "similarity_score": res.get("similarity_score"),
                "evaluation_grade": res.get("grade"),
                "evaluation_reason": res.get("reason")
            })
            
        output = f"data/qa/step4_final_{timestamp}.csv"
        with open(output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Step 4 Completed. Final evaluation saved to {output}")

if __name__ == "__main__":
    main()
