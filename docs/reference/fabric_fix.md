# Fabric Data Agent: Fixing "Duplicate Key" Errors

## The Problem
When deploying Few-Shot Examples to a Fabric Data Agent, you may encounter this error during query execution or agent update:
> **"An item with the same key has already been added. Key: <Your Question Here>"**

This error often persists even after you have code that explicitly "deletes" existing examples before adding new ones.

## Root Cause: "Ghost" Examples
The issue stems from a synchronization gap in the Fabric Data Agent backend (likely Azure AI Search or similar):

1.  **Invisible to Retrieval**: When you call `client.get_fewshots()`, the API returns a list of *visible* examples.
2.  **Persistent in Index**: There can be a state where an example is technically "deleted" or "hidden" from the retrieval list, but its **Key (the Question)** is still locked in the unique index or cache of the backend service.
3.  **The Collision**: Your script sees an empty list from `get_fewshots()`, assumes the slate is clean, and tries to `add_fewshots()`. The backend sees the incoming Key, checks its index, finds the "ghost" entry, and rejects the new addition as a duplicate.

## The Solution: Unique Keys + Cache Busting

Since we cannot forcefully purge the "ghosts" from the backend (as we can't see their IDs to delete them), the solution is to **bypass** them by ensuring every deployment uses globally unique keys.

### Step 1: Append Timestamps to Keys
Modify your deployment script to append a dynamic timestamp to every few-shot question. This guarantees that the Key is unique for every single deployment run.

**Old Code:**
```python
few_shots = {
    "What is the revenue?": "SELECT ..."
}
```

**New Code:**
```python
import time
timestamp = int(time.time())

# Transform all keys to be unique
few_shots = {
    f"{question} (v{timestamp})": sql
    for question, sql in original_few_shots.items()
}
# Result: "What is the revenue? (v1737520000)"
```

### Step 2: Force Configuration Reload (Crucial!)
Fabric Notebooks running in Spark clusters aggressively cache files read from OneLake (FileSystem mounts). Even if you upload the new JSON with timestamped keys, the notebook might still read the *old* content from its cache, causing it to retry the old (colliding) keys.

**The Fix**: Rename your configuration file for every major change or use a versioned filename.

1.  **Deployer**: Save config to `agent_config_v2.json` instead of `agent_config.json`.
2.  **Runner**: Update the notebook script to read `agent_config_v2.json`.

This forces the Spark driver/worker to open a fresh file handle, bypassing the stale file cache.

## Summary Checklist for your other project
1.  [ ] **Dynamic Keys**: Ensure your few-shot loader appends a `(v{time})` suffix.
2.  [ ] **Robust Cleanup**: In your runner, iterate through *whatever* `get_fewshots()` returns and delete them (to keep the active list clean).
3.  [ ] **Cache Bust**: If errors persist, verify your notebook isn't reading a stale config file. Rename the file to prove it.
