#!/usr/bin/env python
# coding: utf-8
"""
Compile agent instructions and upload configuration to Fabric OneLake.

Prerequisites:
    pip install azure-storage-file-datalake azure-identity

Inputs:
    - docs/system_prompts/agent_instructions.md
    - docs/system_prompts/data_instructions.md
    - docs/system_prompts/example_queries.json
Outputs:
    - docs/config/agent_config.json (local)
    - Fabric OneLake Files/agent/agent_config.json (cloud)
"""

import argparse
import csv
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Azure SDK imports
try:
    from azure.identity import InteractiveBrowserCredential
    from azure.storage.filedatalake import DataLakeServiceClient
except ImportError:
    logger.error("Critical Error: Missing Azure SDK packages.")
    logger.error("Please run: pip install azure-storage-file-datalake azure-identity")
    exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
SCRIPT_DIR = Path(__file__).parent
# Go up one level: scripts -> project_root
PROJECT_ROOT = SCRIPT_DIR.parent

# Input Files
AGENT_INSTRUCTIONS = PROJECT_ROOT / "prompts" / "agent" / "agent_instructions.md"
DATA_INSTRUCTIONS = PROJECT_ROOT / "prompts" / "agent" / "data_instructions.md"
FEW_SHOTS_FILE = PROJECT_ROOT / "prompts" / "agent" / "example_queries.json"

# Output/Artifact Files
LOCAL_CONFIG = PROJECT_ROOT / "data" / "agent" / "agent_config.json"
LOCAL_QUERIES = PROJECT_ROOT / "data" / "agent" / "test_queries.json"
LOCAL_RUNNER = PROJECT_ROOT / "scripts" / "platform" / "fabric" / "fabric_runner.py"

# QA Data
QA_DIR = PROJECT_ROOT / "data" / "qa"

FILES_TO_UPLOAD = [LOCAL_CONFIG, LOCAL_QUERIES, LOCAL_RUNNER]

# Fabric API Limits
MAX_DATASOURCE_INSTRUCTIONS: int = 15000
MAX_AGENT_INSTRUCTIONS: int = 15000

# ============================================================================
# COMPILATION FUNCTIONS
# ============================================================================


def read_file(path: Path) -> str:
    """Read file content."""
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    return path.read_text(encoding="utf-8")


def truncate_with_warning(text: str, max_length: int, name: str) -> str:
    """Truncate text if exceeds max length and print warning."""
    if len(text) <= max_length:
        return text
    logger.warning(f"{name} exceeds {max_length:,} char limit ({len(text):,} chars)")
    logger.warning(f"Truncating to {max_length:,} characters...")
    truncated = text[: max_length - 100] + "\n\n[...TRUNCATED DUE TO CHARACTER LIMIT...]"
    return truncated


def sync_qa_failures() -> None:
    logger.info("=" * 60)
    logger.info("STEP 0: SYNCING QA FAILURES")
    logger.info("=" * 60)

    if not QA_DIR.exists():
        logger.warning(f"QA Directory not found: {QA_DIR}")
        return

    # Find the latest step4_final_*.csv
    qa_files = list(QA_DIR.glob("step4_final_*.csv"))
    if not qa_files:
        logger.info("No step4_final_*.csv files found in QA directory. Skipping sync.")
        return

    latest_qa = max(qa_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Analyzing latest QA report: {latest_qa.name}")

    failed_queries: list[dict[str, str]] = []
    try:
        with open(latest_qa, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("evaluation_grade") == "FAIL":
                    question = row.get("question", "").strip()
                    difficulty = row.get("difficulty", "L1").strip()
                    if question:
                        failed_queries.append({"question": question, "complexity": difficulty})

        if failed_queries:
            logger.info(f"Found {len(failed_queries)} failed cases.")
            with open(LOCAL_QUERIES, "w", encoding="utf-8", newline="\n") as f:
                json.dump(failed_queries, f, indent=2, ensure_ascii=False)
            logger.info(f"Updated: {LOCAL_QUERIES.name}")
        else:
            logger.info("No failed cases found in the latest report.")

    except Exception as e:
        logger.error(f"Error processing QA report: {e}")


def compile_configuration() -> None:
    logger.info("=" * 60)
    logger.info("STEP 1: COMPILING AGENT CONFIGURATION")
    logger.info("=" * 60)

    # Read Instructions
    logger.info(f"Reading {AGENT_INSTRUCTIONS.name}...")
    agent_instructions = read_file(AGENT_INSTRUCTIONS)
    agent_instructions = truncate_with_warning(
        agent_instructions, MAX_AGENT_INSTRUCTIONS, "Agent Instructions"
    )

    logger.info(f"Reading {DATA_INSTRUCTIONS.name}...")
    datasource_instructions = read_file(DATA_INSTRUCTIONS)
    datasource_instructions = truncate_with_warning(
        datasource_instructions, MAX_DATASOURCE_INSTRUCTIONS, "Datasource Instructions"
    )

    logger.info(f"Reading {FEW_SHOTS_FILE.name}...")
    with open(FEW_SHOTS_FILE, "r", encoding="utf-8") as f:
        few_shots = json.load(f)

    # Create Config
    compiled_at = datetime.now().isoformat()

    config = {
        "version": "1.0",
        "compiled_at": compiled_at,
        "agent_name": "Sales POA Agent v2",
        "warehouse_name": "DATAAGENT_WH",
        "agent_instructions": agent_instructions,
        "datasource_instructions": datasource_instructions,
        "few_shots": few_shots,
        "selected_tables": [
            {"schema": "ods", "table": "fact_monthly_sales_poa_billing"},
            {"schema": "ods", "table": "fact_monthly_sales_poa_booking"},
            {"schema": "ods", "table": "fact_monthly_sales_poa_budget"},
        ],
    }

    # Write Config
    logger.info(f"Writing {LOCAL_CONFIG.name}...")
    LOCAL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCAL_CONFIG, "w", encoding="utf-8", newline="\n") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved: {LOCAL_CONFIG}")
    logger.info(f"Compiled At: {compiled_at}")


# ============================================================================
# UPLOAD FUNCTIONS
# ============================================================================


def upload_to_onelake(workspace_name: str, lakehouse_name: str, target_folder: str) -> None:
    logger.info("=" * 60)
    logger.info("STEP 2: UPLOADING TO FABRIC ONELAKE")
    logger.info("=" * 60)

    # Authenticate
    logger.info("Authenticating (will open browser window)...")
    credential = InteractiveBrowserCredential()

    # Create DataLake client
    service_client = DataLakeServiceClient(
        account_url="https://onelake.dfs.fabric.microsoft.com", credential=credential
    )

    # Get file system (workspace)
    file_system_client = service_client.get_file_system_client(workspace_name)

    # Get directory client (lakehouse path)
    directory_path = f"{lakehouse_name}.Lakehouse/{target_folder}"
    directory_client = file_system_client.get_directory_client(directory_path)

    logger.info(f"Target: {workspace_name}/{directory_path}")

    # Upload each file
    logger.info(f"Uploading {len(FILES_TO_UPLOAD)} files...")

    for local_file in FILES_TO_UPLOAD:
        if not local_file.exists():
            logger.warning(f"Missing: {local_file.name}")
            continue

        try:
            # Read file content
            content = local_file.read_bytes()

            # Get file client
            file_client = directory_client.get_file_client(local_file.name)

            # Upload (overwrite)
            file_client.upload_data(content, overwrite=True)

            logger.info(f"{local_file.name} ({len(content):,} bytes) uploaded.")

        except Exception as e:
            logger.error(f"{local_file.name}: {e}")

    logger.info("Deployment complete!")
    logger.info(f"Time: {datetime.now().isoformat()}")


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile and deploy Agent config to Fabric OneLake."
    )
    parser.add_argument(
        "--workspace", type=str, default="apac-dp-poc2024", help="Fabric Workspace Name"
    )
    parser.add_argument("--lakehouse", type=str, default="DATAAGENT_LH", help="Lakehouse Name")
    parser.add_argument(
        "--target-folder", type=str, default="Files/agent", help="Target Folder Path"
    )
    args = parser.parse_args()

    try:
        sync_qa_failures()
        compile_configuration()
        upload_to_onelake(args.workspace, args.lakehouse, args.target_folder)
    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}")
        exit(1)


if __name__ == "__main__":
    main()
