#!/usr/bin/env python
# coding: utf-8
"""
Fabric Data Agent Runner

This script runs in a Fabric Notebook and:
1. Loads agent configuration from OneLake synced JSON
2. Updates the data agent with latest instructions
3. Runs test queries and captures full conversation traces
4. Saves detailed logs for Antigravity analysis

Usage:
    Copy this entire script into a Fabric Notebook cell and run it.
"""

import json
import time
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 

from datetime import datetime
from pathlib import Path

# Fabric imports
import sempy.fabric as fabric
from fabric.dataagent.client import (
    FabricDataAgentManagement,
    FabricOpenAI,
    create_data_agent,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Paths in Fabric Lakehouse
# Paths in Fabric Lakehouse
CONFIG_PATH = "/lakehouse/default/Files/agent/agent_config.json"
QUERIES_PATH = "/lakehouse/default/Files/agent/test_queries.json"
LOGS_PATH = "/lakehouse/default/Files/agent/fabric_run_logs.json"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_json(path: str) -> dict:
    """Load JSON from Fabric Lakehouse Files."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict):
    """Save JSON to Fabric Lakehouse Files."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def poll_run(client, thread_id: str, run_id: str, timeout: int = 120) -> object:
    """Poll a run until completion or timeout."""
    start = time.time()
    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id,
        )
        if run.status in ["completed", "failed", "cancelled", "expired"]:
            return run
        
        if time.time() - start > timeout:
            print(f"⚠️  Run timeout after {timeout}s")
            return run
        
        time.sleep(2)

def get_thread_messages(client, thread_id: str) -> list:
    """Retrieve all messages from a thread."""
    response = client.beta.threads.messages.list(
        thread_id=thread_id,
        order="asc"
    )
    messages = []
    for msg in response:
        messages.append({
            "role": msg.role,
            "content": msg.content[0].text.value if msg.content else ""
        })
    return messages

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    run_timestamp = datetime.now().isoformat()
    print("=" * 80)
    print(f"FABRIC DATA AGENT TEST RUN - {run_timestamp}")
    print("=" * 80)
    
    # ------------------------------------------------------------------------
    # 1. LOAD CONFIGURATION
    # ------------------------------------------------------------------------
    print("\n📖 Loading configuration...")
    config = load_json(CONFIG_PATH)
    
    # Version check - helps verify sync
    compiled_at = config.get("compiled_at", "UNKNOWN")
    version = config.get("version", "UNKNOWN")
    print(f"\n" + "=" * 80)
    print(f"🔄 CONFIG VERSION CHECK")
    print(f"   Compiled At: {compiled_at}")
    print(f"   Version: {version}")
    print(f"   (Compare this timestamp with your local compile time to verify sync)")
    print("=" * 80)
    
    agent_name = config["agent_name"]
    warehouse_name = config["warehouse_name"]
    agent_instructions = config["agent_instructions"]
    datasource_instructions = config["datasource_instructions"]
    few_shots = config["few_shots"]
    selected_tables = config["selected_tables"]
    
    print(f"\n   Agent: {agent_name}")
    print(f"   Warehouse: {warehouse_name}")
    print(f"   Instructions: {len(agent_instructions)} chars")
    print(f"   Few Shots: {len(few_shots)} examples")
    
    # ------------------------------------------------------------------------
    # 2. INITIALIZE OR UPDATE AGENT
    # ------------------------------------------------------------------------
    print("\n🤖 Initializing Data Agent...")
    try:
        data_agent = FabricDataAgentManagement(agent_name)
        print(f"   ✅ Connected to existing agent: {agent_name}")
    except:
        print(f"   ⚠️  Agent not found, creating new one...")
        data_agent = create_data_agent(agent_name)
        print(f"   ✅ Created agent: {agent_name}")
    
    # Update agent instructions
    print("\n📝 Updating agent configuration...")
    data_agent.update_configuration(instructions=agent_instructions)
    
    # Add datasource if not exists
    print(f"\n🔗 Checking datasource: {warehouse_name}...")
    existing_sources = data_agent.get_datasources()
    if len(existing_sources) == 0:
        print(f"   Adding warehouse: {warehouse_name}")
        data_agent.add_datasource(warehouse_name, type="warehouse")
    else:
        print(f"   ✅ Datasource already connected ({len(existing_sources)} found)")
    
    # Update datasource configuration
    datasource = data_agent.get_datasources()[0]
    datasource.update_configuration(instructions=datasource_instructions)
    
    # Select tables
    print(f"\n📊 Selecting {len(selected_tables)} tables...")
    for tbl in selected_tables:
        try:
            datasource.select(tbl["schema"], tbl["table"])
            print(f"   ✓ {tbl['schema']}.{tbl['table']}")
        except Exception as e:
            print(f"   ✗ {tbl['schema']}.{tbl['table']} - {e}")
    
    # Add few-shot examples
    print(f"\n💡 Adding {len(few_shots)} few-shot examples...")
    # First, clear existing few-shots (optional)
    existing_fewshots = datasource.get_fewshots()
    for fs in existing_fewshots:
        try:
            datasource.remove_fewshot(fs["id"])
        except:
            pass
    
    # Add new few-shots (with dynamic keys to avoid duplicates)
    timestamp_suffix = int(time.time())
    unique_few_shots = {
        f"{q} (v{timestamp_suffix})": sql 
        for q, sql in few_shots.items()
    }
    
    datasource.add_fewshots(unique_few_shots)
    print(f"   ✅ Few-shots updated (v{timestamp_suffix})")
    
    # Publish agent
    print("\n🚀 Publishing agent...")
    data_agent.publish()
    print("   ✅ Agent published")
    
    # ------------------------------------------------------------------------
    # 3. LOAD TEST QUERIES
    # ------------------------------------------------------------------------
    print("\n📋 Loading test queries...")
    test_queries = load_json(QUERIES_PATH)
    print(f"   Found {len(test_queries)} test queries")
    
    # ------------------------------------------------------------------------
    # 4. RUN TESTS
    # ------------------------------------------------------------------------
    print("\n🧪 Running tests...")
    print("=" * 80)
    
    # Initialize OpenAI client
    fabric_client = FabricOpenAI(artifact_name=agent_name)
    assistant = fabric_client.beta.assistants.create(model="gpt-4.1-mini")
    
    results = []
    
    for i, query_obj in enumerate(test_queries, 1):
        query_id = query_obj.get("id", f"Q{i:03d}")
        question = query_obj["question"]
        complexity = query_obj.get("complexity", "SIMPLE")
        
        print(f"\n[{i}/{len(test_queries)}] {query_id}: {question}")
        print(f"   Complexity: {complexity}")
        
        test_result = {
            "id": query_id,
            "question": question,
            "complexity": complexity,
            "timestamp": datetime.now().isoformat(),
        }
        
        try:
            # Create thread
            thread = fabric_client.beta.threads.create()
            
            # Send message
            fabric_client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=question,
            )
            
            # Create run
            run = fabric_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            # Poll for completion
            run = poll_run(fabric_client, thread.id, run.id)
            
            test_result["status"] = run.status
            
            # Retrieve messages
            messages = get_thread_messages(fabric_client, thread.id)
            test_result["messages"] = messages
            
            # Extract answer
            if len(messages) > 1:
                answer = messages[-1]["content"]
                test_result["answer"] = answer
                print(f"   ✅ Status: {run.status}")
                print(f"   📝 Answer preview: {answer[:200]}...")
            else:
                test_result["answer"] = ""
                print(f"   ⚠️  No response generated")
            
            # Clean up
            fabric_client.beta.threads.delete(thread.id)
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            test_result["status"] = "error"
            test_result["error"] = str(e)
            test_result["answer"] = ""
        
        results.append(test_result)
        time.sleep(1)  # Rate limiting
    
    # ------------------------------------------------------------------------
    # 5. SAVE LOGS
    # ------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"💾 Saving logs to {LOGS_PATH}...")
    
    log_data = {
        "run_timestamp": run_timestamp,
        "agent_name": agent_name,
        "warehouse_name": warehouse_name,
        "config": {
            "agent_instructions_length": len(agent_instructions),
            "datasource_instructions_length": len(datasource_instructions),
            "few_shots_count": len(few_shots),
            "selected_tables_count": len(selected_tables),
        },
        "total_queries": len(test_queries),
        "results": results,
        "summary": {
            "completed": sum(1 for r in results if r.get("status") == "completed"),
            "failed": sum(1 for r in results if r.get("status") in ["failed", "error"]),
        }
    }
    
    save_json(LOGS_PATH, log_data)
    
    print(f"   ✅ Logs saved successfully")
    print(f"   Completed: {log_data['summary']['completed']}/{len(test_queries)}")
    print(f"   Failed: {log_data['summary']['failed']}/{len(test_queries)}")
    print("=" * 80)
    print(f"   OneLake will sync {LOGS_PATH} to your local machine.")
    print("=" * 80)

def keep_alive():
    """Keep the notebook session active."""
    print("\n" + "=" * 80)
    print("💤 KEEP ALIVE MODE ACTIVE")
    print("   The script has finished (or errored), but this loop keeps the notebook active.")
    print("   Stop the cell manually to exit.")
    print("=" * 80)
    
    try:
        while True:
            time.sleep(60)  # Sleep 1 minute
            # Print a small dot or timestamp occasionally to show it's alive
            # timestamp = datetime.now().strftime("%H:%M:%S")
            # print(f"   ... active {timestamp}")
    except KeyboardInterrupt:
        print("\n👋 Keep-alive stopped by user.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ FATAL ERROR IN SCRIPT: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        keep_alive()
