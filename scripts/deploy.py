#!/usr/bin/env python
# coding: utf-8
"""
Deploy Agent to Fabric (Compile + Upload)

This script:
1. Compiles the agent configuration from local markdown instructions.
2. Generates the 'agent_config.json' file.
3. Uploads the config, runner, and queries to Fabric OneLake.

Prerequisites:
    pip install azure-storage-file-datalake azure-identity
"""

import json
import time
from pathlib import Path
from datetime import datetime

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

# Input Files
AGENT_INSTRUCTIONS = PROJECT_ROOT / "docs" / "system_prompts" / "agent_instructions.md"
DATA_INSTRUCTIONS = PROJECT_ROOT / "docs" / "system_prompts" / "data_instructions.md"
FEW_SHOTS_FILE = PROJECT_ROOT / "docs" / "system_prompts" / "example_queries.json"

# Output/Artifact Files
LOCAL_CONFIG = PROJECT_ROOT / "docs" / "config" / "agent_config.json"
LOCAL_QUERIES = PROJECT_ROOT / "docs" / "config" / "test_queries.json"
LOCAL_RUNNER = PROJECT_ROOT / "scripts" / "fabric" / "fabric_runner.py"

FILES_TO_UPLOAD = [LOCAL_CONFIG, LOCAL_QUERIES, LOCAL_RUNNER]

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
    print(f"⚠️  WARNING: {name} exceeds {max_length:,} char limit ({len(text):,} chars)")
    print(f"   Truncating to {max_length:,} characters...")
    truncated = text[:max_length - 100] + "\n\n[...TRUNCATED DUE TO CHARACTER LIMIT...]"
    return truncated

def compile_configuration():
    print("=" * 60)
    print("STEP 1: COMPILING AGENT CONFIGURATION")
    print("=" * 60)
    
    # Read Instructions
    print(f"\n📖 Reading {AGENT_INSTRUCTIONS.name}...")
    agent_instructions = read_file(AGENT_INSTRUCTIONS)
    agent_instructions = truncate_with_warning(agent_instructions, MAX_AGENT_INSTRUCTIONS, "Agent Instructions")
    
    print(f"📖 Reading {DATA_INSTRUCTIONS.name}...")
    datasource_instructions = read_file(DATA_INSTRUCTIONS)
    datasource_instructions = truncate_with_warning(datasource_instructions, MAX_DATASOURCE_INSTRUCTIONS, "Datasource Instructions")
    
    print(f"📖 Reading {FEW_SHOTS_FILE.name}...")
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
            {"schema": "ods", "table": "fact_monthly_sales_poa_booking"}
        ]
    }
    
    # Write Config
    print(f"\n💾 Writing {LOCAL_CONFIG.name}...")
    LOCAL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCAL_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ Saved: {LOCAL_CONFIG}")
    print(f"   Compiled At: {compiled_at}")
    print("-" * 60)

# ============================================================================
# UPLOAD FUNCTIONS
# ============================================================================

def upload_to_onelake():
    print("\n" + "=" * 60)
    print("STEP 2: UPLOADING TO FABRIC ONELAKE")
    print("=" * 60)
    
    # Authenticate
    print("\n🔐 Authenticating (will open browser window)...")
    credential = InteractiveBrowserCredential()
    
    # Create DataLake client
    service_client = DataLakeServiceClient(
        account_url=ONELAKE_URL,
        credential=credential
    )
    
    # Get file system (workspace)
    file_system_client = service_client.get_file_system_client(WORKSPACE_NAME)
    
    # Get directory client (lakehouse path)
    directory_path = f"{LAKEHOUSE_NAME}.Lakehouse/{TARGET_FOLDER}"
    directory_client = file_system_client.get_directory_client(directory_path)
    
    print(f"\n📂 Target: {WORKSPACE_NAME}/{directory_path}")
    
    # Upload each file
    print(f"\n📤 Uploading {len(FILES_TO_UPLOAD)} files...")
    
    for local_file in FILES_TO_UPLOAD:
        if not local_file.exists():
            print(f"   ⚠️  Missing: {local_file.name}")
            continue
        
        try:
            # Read file content
            content = local_file.read_bytes()
            
            # Get file client
            file_client = directory_client.get_file_client(local_file.name)
            
            # Upload (overwrite)
            file_client.upload_data(content, overwrite=True)
            
            print(f"   ✅ {local_file.name} ({len(content):,} bytes)")
            
        except Exception as e:
            print(f"   ❌ {local_file.name}: {e}")
    
    print(f"\n✅ Deployment complete!")
    print(f"   Time: {datetime.now().isoformat()}")
    print("=" * 60)

# ============================================================================
# MAIN
# ============================================================================

def main():
    try:
        compile_configuration()
        upload_to_onelake()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()
