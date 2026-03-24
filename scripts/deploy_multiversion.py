#!/usr/bin/env python
# coding: utf-8
"""
Compile and upload MULTIPLE VERSIONS of agent instructions and configuration to Fabric OneLake.

Versions:
    - v2: Uses *_20260210 files
    - v3: Uses standard files (latest)

Outputs:
    - agent_config_v2.json -> Fabric Files/agent/agent_config_v2.json
    - fabric_runner_v2.py  -> Fabric Files/agent/fabric_runner_v2.py
    - agent_config_v3.json -> Fabric Files/agent/agent_config_v3.json
    - fabric_runner_v3.py  -> Fabric Files/agent/fabric_runner_v3.py
"""

import json
from datetime import datetime
from pathlib import Path

# Azure SDK imports
try:
    from azure.identity import InteractiveBrowserCredential
    from azure.storage.filedatalake import DataLakeServiceClient
except ImportError:
    print("❌ Critical Error: Missing Azure SDK packages.")
    print("   Please run: pip install azure-storage-file-datalake azure-identity")
    exit(1)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Input Files (Standard / V3)
V3_AGENT_INSTRUCTIONS = PROJECT_ROOT / "prompts" / "agent" / "agent_instructions.md"
V3_DATA_INSTRUCTIONS = PROJECT_ROOT / "prompts" / "agent" / "data_instructions.md"
V3_FEW_SHOTS_FILE = PROJECT_ROOT / "prompts" / "agent" / "example_queries.json"

# Input Files (V2 - Frozen 20260210)
V2_AGENT_INSTRUCTIONS = PROJECT_ROOT / "prompts" / "agent" / "agent_instructions_20260210.md"
V2_DATA_INSTRUCTIONS = PROJECT_ROOT / "prompts" / "agent" / "data_instructions_20260210.md"
V2_FEW_SHOTS_FILE = PROJECT_ROOT / "prompts" / "agent" / "example_queries_20260210.json"

# Config Input
TEST_QUERIES_FILE = PROJECT_ROOT / "data" / "agent" / "test_queries.json"

# Base Runner Script
BASE_RUNNER_SCRIPT = PROJECT_ROOT / "scripts" / "platform" / "fabric" / "fabric_runner.py"

# Temporary Output Directory
OUTPUT_DIR = PROJECT_ROOT / "data" / "agent_deploy_temp"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Fabric API Limits
MAX_DATASOURCE_INSTRUCTIONS = 15000
MAX_AGENT_INSTRUCTIONS = 15000

# OneLake Configuration
ONELAKE_ACCOUNT = "onelake"
ONELAKE_URL = f"https://{ONELAKE_ACCOUNT}.dfs.fabric.microsoft.com"
WORKSPACE_NAME = "apac-dp-poc2024"
LAKEHOUSE_NAME = "DATAAGENT_LH"
TARGET_FOLDER = "Files/agent"

# ============================================================================
# DEFINITIONS
# ============================================================================

VERSIONS = [
    {
        "id": "v2",
        "agent_name": "Sales POA Agent v2",
        "files": {
            "agent": V2_AGENT_INSTRUCTIONS,
            "data": V2_DATA_INSTRUCTIONS,
            "fewshots": V2_FEW_SHOTS_FILE,
        },
    },
    {
        "id": "v3",
        "agent_name": "Sales POA Agent v3",
        "files": {
            "agent": V3_AGENT_INSTRUCTIONS,
            "data": V3_DATA_INSTRUCTIONS,
            "fewshots": V3_FEW_SHOTS_FILE,
        },
    },
]

# ============================================================================
# FUNCTIONS
# ============================================================================


def read_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}")
    return path.read_text(encoding="utf-8")


def truncate_with_warning(text: str, max_length: int, name: str) -> str:
    if len(text) <= max_length:
        return text
    print(f"WARNING: {name} exceeds {max_length:,} char limit ({len(text):,} chars)")
    print(f"   Truncating to {max_length:,} characters...")
    truncated = text[: max_length - 100] + "\n\n[...TRUNCATED DUE TO CHARACTER LIMIT...]"
    return truncated


def compile_config(version_id, agent_name, files):
    print(f"   Compiling configuration for {version_id} ({agent_name})...")

    # Read Content
    agent_instr = read_file(files["agent"])
    agent_instr = truncate_with_warning(
        agent_instr, MAX_AGENT_INSTRUCTIONS, f"{version_id} Agent Instructions"
    )

    data_instr = read_file(files["data"])
    data_instr = truncate_with_warning(
        data_instr, MAX_DATASOURCE_INSTRUCTIONS, f"{version_id} Data Instructions"
    )

    with open(files["fewshots"], "r", encoding="utf-8") as f:
        few_shots = json.load(f)

    # Create Config Object
    compiled_at = datetime.now().isoformat()
    config = {
        "version": version_id,
        "compiled_at": compiled_at,
        "agent_name": agent_name,
        "warehouse_name": "DATAAGENT_WH",
        "agent_instructions": agent_instr,
        "datasource_instructions": data_instr,
        "few_shots": few_shots,
        "selected_tables": [
            {"schema": "ods", "table": "fact_monthly_sales_poa_billing"},
            {"schema": "ods", "table": "fact_monthly_sales_poa_booking"},
            {"schema": "ods", "table": "fact_monthly_sales_poa_budget"},
        ],
    }

    # Write to temp file
    output_filename = f"agent_config_{version_id}.json"
    output_path = OUTPUT_DIR / output_filename
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return output_path


def generate_runner(version_id):
    print(f"   Generating runner script for {version_id}...")

    base_script = read_file(BASE_RUNNER_SCRIPT)

    # Replace Paths
    # Original: CONFIG_PATH = "/lakehouse/default/Files/agent/agent_config.json"
    # New:      CONFIG_PATH = "/lakehouse/default/Files/agent/agent_config_{version_id}.json"

    # Original: LOGS_PATH = "/lakehouse/default/Files/agent/fabric_run_logs.json"
    # New:      LOGS_PATH = "/lakehouse/default/Files/agent/fabric_run_logs_{version_id}.json"

    new_script = base_script.replace(
        "/lakehouse/default/Files/agent/agent_config.json",
        f"/lakehouse/default/Files/agent/agent_config_{version_id}.json",
    ).replace(
        "/lakehouse/default/Files/agent/fabric_run_logs.json",
        f"/lakehouse/default/Files/agent/fabric_run_logs_{version_id}.json",
    )

    # Also update the docstring to be clear
    new_script = new_script.replace("agent_config.json", f"agent_config_{version_id}.json")

    output_filename = f"fabric_runner_{version_id}.py"
    output_path = OUTPUT_DIR / output_filename
    output_path.write_text(new_script, encoding="utf-8")

    return output_path


def upload_files(files_to_upload):
    print("\n" + "=" * 60)
    print("STEP 2: UPLOADING TO FABRIC ONELAKE")
    print("=" * 60)

    # Authenticate
    print("\nAuthenticating (will open browser window)...")
    credential = InteractiveBrowserCredential()

    # Create DataLake client
    service_client = DataLakeServiceClient(account_url=ONELAKE_URL, credential=credential)

    # Get file system (workspace)
    file_system_client = service_client.get_file_system_client(WORKSPACE_NAME)

    # Get directory client (lakehouse path)
    directory_path = f"{LAKEHOUSE_NAME}.Lakehouse/{TARGET_FOLDER}"
    directory_client = file_system_client.get_directory_client(directory_path)

    print(f"\nTarget: {WORKSPACE_NAME}/{directory_path}")
    print(f"Uploading {len(files_to_upload)} files...")

    for local_file in files_to_upload:
        if not local_file.exists():
            print(f"Missing: {local_file.name}")
            continue

        try:
            content = local_file.read_bytes()
            file_client = directory_client.get_file_client(local_file.name)
            file_client.upload_data(content, overwrite=True)
            print(f"✅ {local_file.name} ({len(content):,} bytes)")
        except Exception as e:
            print(f"❌ {local_file.name}: {e}")


def main():
    print("=" * 60)
    print("DEPLOY MULTI-VERSION AGENTS (V2 & V3)")
    print("=" * 60)

    files_to_upload = []

    # 1. Compile Configs and Runners
    for ver in VERSIONS:
        print(f"\nProcessing {ver['id']}...")
        config_path = compile_config(ver["id"], ver["agent_name"], ver["files"])
        runner_path = generate_runner(ver["id"])

        files_to_upload.append(config_path)
        files_to_upload.append(runner_path)

    # Add Test Queries (Shared)
    if TEST_QUERIES_FILE.exists():
        files_to_upload.append(TEST_QUERIES_FILE)

    # 2. Upload
    upload_files(files_to_upload)

    print("\ndeployment Complete!")


if __name__ == "__main__":
    main()
