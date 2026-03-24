#!/usr/bin/env python
# coding: utf-8
"""
Sync log files directly from Fabric OneLake using the Azure Data Lake Storage API.

Prerequisites:
    pip install azure-storage-file-datalake azure-identity

Inputs:
    - Fabric OneLake Files/agent/fabric_run_logs.json
Outputs:
    - docs/process/fabric_run_logs.json
"""

import json
from pathlib import Path

# Azure SDK imports
from azure.identity import InteractiveBrowserCredential
from azure.storage.filedatalake import DataLakeServiceClient

# ============================================================================
# CONFIGURATION
# ============================================================================


# Local paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
LOCAL_LOGS = PROJECT_ROOT / "logs" / "remote" / "fabric_run_logs.json"

# OneLake configuration
ONELAKE_ACCOUNT = "onelake"
ONELAKE_URL = f"https://{ONELAKE_ACCOUNT}.dfs.fabric.microsoft.com"

# Your workspace and lakehouse names
WORKSPACE_NAME = "apac-dp-poc2024"
LAKEHOUSE_NAME = "DATAAGENT_LH"
TARGET_FOLDER = "Files/agent"
LOG_FILE = "fabric_run_logs.json"

# ============================================================================
# SYNC FUNCTIONS
# ============================================================================


def sync_logs():
    print("=" * 60)
    print("DOWNLOADING LOGS FROM FABRIC ONELAKE (Direct API)")
    print("=" * 60)

    # Authenticate
    print("\n🔐 Authenticating (will open browser window)...")
    credential = InteractiveBrowserCredential()

    # Create DataLake client
    service_client = DataLakeServiceClient(account_url=ONELAKE_URL, credential=credential)

    # Get file system (workspace)
    file_system_client = service_client.get_file_system_client(WORKSPACE_NAME)

    # Get file client
    file_path = f"{LAKEHOUSE_NAME}.Lakehouse/{TARGET_FOLDER}/{LOG_FILE}"
    file_client = file_system_client.get_file_client(file_path)

    print(f"\n📂 Source: {WORKSPACE_NAME}/{file_path}")

    try:
        # Download file
        print(f"\n📥 Downloading {LOG_FILE}...")
        download = file_client.download_file()
        content = download.readall()

        # Ensure directory exists
        LOCAL_LOGS.parent.mkdir(parents=True, exist_ok=True)

        # Save locally
        LOCAL_LOGS.write_bytes(content)
        print(f"   ✅ Saved: {LOCAL_LOGS}")
        print(f"   Size: {len(content):,} bytes")

        # Parse and show summary
        data = json.loads(content.decode("utf-8"))

        print("\n📊 Run Summary:")
        print(f"   Timestamp: {data.get('run_timestamp', 'N/A')}")
        print(f"   Agent: {data.get('agent_name', 'N/A')}")
        print(f"   Queries: {data.get('total_queries', 0)}")

        summary = data.get("summary", {})
        print(f"   ✅ Completed: {summary.get('completed', 0)}")
        print(f"   ❌ Failed: {summary.get('failed', 0)}")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("   (Ensure the file exists on OneLake and you have permissions)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    sync_logs()
