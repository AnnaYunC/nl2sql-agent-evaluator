"""Step 1: Question Generation logic."""
import os
import json
import csv
import time

def load_prompt(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def generate_questions(client_openai, model, schema_context, prompt_dir, metrics, dimensions, target_level=None, count=2):
    level_files = {
        "L1": "l1_atomic.md",
        "L2": "l2_filtering.md",
        "L3": "l3_grouping.md",
        "L4": "l4_ratios.md",
        "L5": "l5_time_series.md"
    }
    
    results = []
    # If target_level is a list (from CLI), process each. If string, wrap in list.
    target_levels = [target_level] if isinstance(target_level, str) else target_level
    
    items_to_process = {}
    if target_levels:
        for lvl in target_levels:
            if lvl in level_files:
                items_to_process[lvl] = level_files[lvl]
    else:
        items_to_process = level_files

    for level, filename in items_to_process.items():
        print(f"Generating {count} questions for {level}...")
        prompt = load_prompt(os.path.join(prompt_dir, filename))
        if not prompt: continue
        
        intents = [f"Analyze {m}" for m in metrics[:count]]
        
        for intent in intents:
            try:
                resp = client_openai.chat.completions.create(
                    model=model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": f"{prompt}\n\nSCHEMA:\n{schema_context}\n\nDATE_CONSTRAINT: The available sales data range is only from '2022-01' to '2025-10'. Do NOT generate questions outside this range."},
                        {"role": "user", "content": f"Generate one QA for: {intent}"}
                    ]
                )
                data = json.loads(resp.choices[0].message.content)
                results.append({
                    "difficulty": data.get("difficulty", level),
                    "question": data.get("question", ""),
                    "metric": data.get("metric", "N/A"),
                    "dimension": data.get("dimension", "N/A")
                })
                time.sleep(0.5)
            except Exception as e:
                print(f"Error in {level}: {e}")
    return results
