import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from sales_agent.core.client import FabricDataAgentClient
from sales_agent.pipeline import evaluator, executor, ground_truth_gen, question_gen

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sales Agent Testing Pipeline")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4], help="Run specific step only")
    parser.add_argument(
        "--level",
        type=str,
        nargs="+",
        choices=["L1", "L2", "L3", "L4", "L5"],
        help="Level(s) to generate (for step 1)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=2,
        help="Number of questions to generate per level (for step 1)",
    )
    parser.add_argument("--input", type=str, help="Input CSV (for steps > 1)")
    parser.add_argument(
        "--output-dir", type=str, default="data/qa", help="Output directory for QA artifacts"
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(args.output_dir, exist_ok=True)

    openai_client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")
    )
    model = os.getenv("LLM_MODEL", "gpt-5-nano")

    # Step 1: Question Generation
    if not args.step or args.step == 1:
        logger.info("Step 1: Generating Questions...")

        config_path = os.path.join(args.output_dir, "generation_config.json")
        if not os.path.exists(config_path):
            logger.error(f"Config file {config_path} not found.")
            return

        with open(config_path, "r", encoding="utf-8") as f:
            gen_config = json.load(f)

        metrics = gen_config.get("metrics", [])
        dimensions = gen_config.get("dimensions", {})

        schema = ""
        with open("prompts/agent/data_instructions.md", "r", encoding="utf-8") as f:
            schema = f.read()

        questions = question_gen.generate_questions(
            openai_client,
            model,
            schema,
            "prompts/qa",
            metrics,
            dimensions,
            target_level=args.level,
            count=args.count,
        )
        output = os.path.join(args.output_dir, f"step1_questions_{timestamp}.csv")
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["difficulty", "question", "metric", "dimension"],
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
            writer.writerows(questions)
        logger.info(f"Step 1 Completed. Questions saved to {output}")
        if args.step == 1:
            return
        args.input = output

    # Step 2: Ground Truth
    if not args.step or args.step == 2:
        logger.info("Step 2: Generating Ground Truth...")
        rows: list[dict] = []
        input_csv = args.input or os.path.join(args.output_dir, "step1_questions.csv")
        if not os.path.exists(input_csv):
            import glob

            files = sorted(
                glob.glob(os.path.join(args.output_dir, "step1_questions_*.csv")), reverse=True
            )
            if files:
                input_csv = files[0]
            else:
                logger.error("Step 1 output not found. Please run Step 1 or provide --input.")
                return

        with open(input_csv, "r", encoding="utf-8") as f:
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
            logger.info(f"Generating GT for: {r['question'][:50]}...")
            r["expected_answer"] = ground_truth_gen.generate_ground_truth(
                openai_client, model, r["question"], context
            )

        output = os.path.join(args.output_dir, f"step2_truth_{timestamp}.csv")
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"Step 2 Completed. Ground truth saved to {output}")
        if args.step == 2:
            return
        args.input = output

    # Step 3: Execution
    if not args.step or args.step == 3:
        logger.info("Step 3: Running Agent...")
        rows = []
        input_csv = args.input or os.path.join(args.output_dir, "step2_truth.csv")
        if not os.path.exists(input_csv):
            import glob

            files = sorted(
                glob.glob(os.path.join(args.output_dir, "step2_truth_*.csv")), reverse=True
            )
            if files:
                input_csv = files[0]
            else:
                logger.error("Step 2 output not found. Please run Step 2 or provide --input.")
                return

        with open(input_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        fabric = FabricDataAgentClient(os.getenv("TENANT_ID"), os.getenv("DATA_AGENT_URL"))
        total = len(rows)
        for i, r in enumerate(rows, 1):
            logger.info(f"[{i}/{total}] Running Agent for question: {r['question'][:60]}...")
            res = executor.run_agent(fabric, r["question"])
            r["agent_answer"] = res["answer"]
            r["generated_sql"] = res["sql"]

        output = os.path.join(args.output_dir, f"step3_results_{timestamp}.csv")
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"Execution results saved to {output}")
        if args.step == 3:
            return
        args.input = output

    # Step 4: Evaluation
    if not args.step or args.step == 4:
        logger.info("Step 4: Evaluating...")
        rows = []
        input_csv = args.input or os.path.join(args.output_dir, "step3_results.csv")
        if not os.path.exists(input_csv):
            import glob

            files = sorted(
                glob.glob(os.path.join(args.output_dir, "step3_results_*.csv")), reverse=True
            )
            if files:
                input_csv = files[0]
            else:
                logger.error("Step 3 output not found. Please run Step 3 or provide --input.")
                return

        with open(input_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        total = len(rows)
        for i, r in enumerate(rows, 1):
            logger.info(f"[{i}/{total}] Evaluating: {r['question'][:60]}...")
            res = evaluator.evaluate(
                openai_client,
                model,
                r["difficulty"],
                r["question"],
                r["expected_answer"],
                r["agent_answer"],
            )
            r.update(
                {
                    "similarity_score": res.get("similarity_score"),
                    "evaluation_grade": res.get("grade"),
                    "evaluation_reason": res.get("reason"),
                }
            )

        output = os.path.join(args.output_dir, f"step4_final_{timestamp}.csv")
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"Step 4 Completed. Final evaluation saved to {output}")


if __name__ == "__main__":
    main()
