#!/usr/bin/env python3
import json
import os
import time
import uuid
import warnings
from typing import Optional

import requests
from azure.identity import InteractiveBrowserCredential
from openai import OpenAI

# Suppress OpenAI Assistants API deprecation warnings
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=r".*Assistants API is deprecated.*"
)


class TokenCache:
    def __init__(self, cache_file: str = ".fabric_token_cache"):
        self.cache_file = cache_file

    def load(self) -> Optional[dict]:
        try:
            if not os.path.exists(self.cache_file):
                return None
            with open(self.cache_file, "r") as f:
                data = json.load(f)
            if "token" not in data or "expires_on" not in data:
                return None
            if data["expires_on"] <= (time.time() + 300):
                return None
            return data
        except Exception:
            return None

    def save(self, token: str, expires_on: float):
        try:
            data = {"token": token, "expires_on": expires_on}
            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


class FabricDataAgentClient:
    def __init__(self, tenant_id: str, data_agent_url: str):
        self.tenant_id = tenant_id
        self.data_agent_url = data_agent_url
        self.credential = None
        self.token = None
        self.token_cache = TokenCache()

        if not tenant_id or not data_agent_url:
            raise ValueError("tenant_id and data_agent_url are required")

        cached_token = self.token_cache.load()
        if cached_token:
            print("Fabric Client: Using cached token.")
            from collections import namedtuple

            AccessToken = namedtuple("AccessToken", ["token", "expires_on"])
            self.token = AccessToken(
                token=cached_token["token"], expires_on=cached_token["expires_on"]
            )
        else:
            self._authenticate()

    def _authenticate(self):
        print("Fabric Client: Initiating Interactive Browser Authentication...")
        self.credential = InteractiveBrowserCredential(tenant_id=self.tenant_id)
        self._refresh_token()

    def _refresh_token(self):
        if self.credential is None:
            self.credential = InteractiveBrowserCredential(tenant_id=self.tenant_id)
        print("Fabric Client: Fetching access token...")
        self.token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
        print("Fabric Client: Token acquired successfully.")
        self.token_cache.save(self.token.token, self.token.expires_on)

    def _get_openai_client(self) -> OpenAI:
        if self.token and self.token.expires_on <= (time.time() + 300):
            self._refresh_token()
        return OpenAI(
            api_key="",
            base_url=self.data_agent_url,
            default_query={"api-version": "2024-05-01-preview"},
            default_headers={
                "Authorization": f"Bearer {self.token.token}",
                "ActivityId": str(uuid.uuid4()),
            },
        )

    def get_run_details(self, question: str) -> dict:
        client = self._get_openai_client()
        assistant = client.beta.assistants.create(model="not used")

        # Create thread
        base_url = self.data_agent_url.removesuffix("/openai").replace(
            "/aiassistant", "/__private/aiassistant"
        )
        thread_name = f"pipeline-thread-{uuid.uuid4()}"
        headers = {
            "Authorization": f"Bearer {self.token.token}",
            "Content-Type": "application/json",
        }
        resp = requests.get(f'{base_url}/threads/fabric?tag="{thread_name}"', headers=headers)
        resp.raise_for_status()
        thread_id = resp.json()["id"]

        client.beta.threads.messages.create(thread_id=thread_id, role="user", content=question)
        run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant.id)

        while run.status in ["queued", "in_progress"]:
            time.sleep(2)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        steps = client.beta.threads.runs.steps.list(thread_id=thread_id, run_id=run.id)
        messages = client.beta.threads.messages.list(thread_id=thread_id, order="asc")

        # Enhanced SQL extraction for Fabric Data Agent
        sql_queries = []
        import re

        # Helper to clean and add SQL
        def add_sql(query_text):
            if not query_text:
                return
            cleaned = query_text.strip().strip("`")
            if cleaned.upper().startswith("SELECT") and cleaned not in sql_queries:
                sql_queries.append(cleaned)

        # 1. Extract from Tool Calls (Structured)
        for step in steps.data:
            if hasattr(step.step_details, "tool_calls"):
                for tc in step.step_details.tool_calls:
                    if hasattr(tc, "function"):
                        # Check arguments
                        try:
                            args = json.loads(tc.function.arguments)
                            if "sql" in args and isinstance(args["sql"], str):
                                add_sql(args["sql"])
                        except:
                            pass

                        # Check output (Tool Output)
                        output = getattr(tc.function, "output", "")
                        if output:
                            # Markdown blocks
                            code_blocks = re.findall(
                                r"```sql\n(.*?)\n```", output, re.DOTALL | re.IGNORECASE
                            )
                            for block in code_blocks:
                                add_sql(block)

        # 2. Extract from Assistant Message (Text Answer)
        # This is critical if the agent puts SQL in the text response but not as a tool output
        answer_text = ""
        for msg in messages.data:
            if msg.role == "assistant":
                content = (
                    msg.content[0].text.value
                    if hasattr(msg.content[0], "text")
                    else str(msg.content[0])
                )
                answer_text = content  # Keep last answer

                # Look for SQL in code blocks
                code_blocks = re.findall(r"```sql\n(.*?)\n```", content, re.DOTALL | re.IGNORECASE)
                for block in code_blocks:
                    add_sql(block)

                # Fallback: Look for SQL inside <details>...</details> or generic unformatted blocks
                # We specifically look for lines starting with SELECT inside the content
                # This regex captures SELECT ... until a likely end (double newline or </details>)
                if "SELECT " in content.upper() and not code_blocks:
                    # Try to find a block that looks like SQL
                    # Capture SELECT followed by anything until valid end
                    # Minimal extraction: SELECT ... FROM ... WHERE ...
                    candidates = re.findall(
                        r"(SELECT\s[\s\S]+?(?:;|\n\n|<\/details>|```))", content, re.IGNORECASE
                    )
                    for cand in candidates:
                        # cleanup the end marker
                        cand = re.sub(r"(?:;|\n\n|<\/details>|```)$", "", cand)
                        add_sql(cand)

        answer = ""
        for msg in messages.data:
            if msg.role == "assistant":
                answer = (
                    msg.content[0].text.value
                    if hasattr(msg.content[0], "text")
                    else str(msg.content[0])
                )

        try:
            client.beta.threads.delete(thread_id=thread_id)
        except:
            pass

        return {"answer": answer, "sql_analysis": {"sql_queries": sql_queries}}
