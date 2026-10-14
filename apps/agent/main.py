"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""

import json
import logging
import os
from pathlib import Path
import warnings

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from copilotkit import CopilotKitMiddleware
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from deepagents import create_deep_agent

from src.anthropic_compat import ConsecutiveSystemMessagesMiddleware
from src.bounded_memory_saver import BoundedMemorySaver
from src.model import build_model, RequestModelMiddleware, CredentialScopedModel
from src.credentials import (
    CredentialsMiddleware,
    CredentialScopedAgent,
    current_credentials,
    validate_credentials,
)
from src.provider_config import answer_model, answer_provider, openai_base_url, jev_api_url
from src.visualization_router import JevVisualizationMiddleware
from src.skill_backend import SKILL_SOURCES, build_agent_backend
from src.query import query_data
from src.todos import AgentState, todo_tools
from src.form import generate_form
from src.trip_images import get_trip_stop_images
from src.plan import plan_visualization
from src.prompt import SYSTEM_PROMPT

load_dotenv()

# Source marker plus the exact commit recorded by the Zerops build. No secrets
# or Authorization headers are included. This distinguishes a fresh deployment
# from restarting or redeploying an older saved application version.
PROVIDER_CONFIG_VERSION = "env-router-v2"
_revision_file = Path(__file__).with_name("DEPLOY_REVISION")
_deployed_revision = _revision_file.read_text(encoding="utf-8").strip() if _revision_file.is_file() else "not-recorded"
_provider = answer_provider()
logging.getLogger("uvicorn.error").info(
    "[oiui-startup] %s",
    json.dumps({
        "config_version": PROVIDER_CONFIG_VERSION,
        "revision": _deployed_revision,
        "provider_mode": os.environ.get("PROVIDER_KEYS_MODE", "byok"),
        "answer_provider": _provider,
        "answer_model": answer_model(),
        "openai_base_url": openai_base_url() if _provider == "openai" else "not-used",
        "jev_api_url": jev_api_url(),
        "jev_model": os.environ.get("JEV_MODEL", "jev-latest"),
        "answer_key_set": bool(os.environ.get("OPENAI_API_KEY" if _provider == "openai" else "ANTHROPIC_API_KEY", "").strip()),
        "jev_key_set": bool(os.environ.get("TYPESAFE_API_KEY", "").strip()),
    }),
)

agent = create_deep_agent(
    model=CredentialScopedModel(fallback=build_model(allow_unconfigured=True)),
    tools=[query_data, get_trip_stop_images, plan_visualization, *todo_tools, generate_form],
    middleware=[
        RequestModelMiddleware(),
        CopilotKitMiddleware(),
        JevVisualizationMiddleware(),
        ConsecutiveSystemMessagesMiddleware(),
    ],
    context_schema=AgentState,
    skills=SKILL_SOURCES,
    backend=build_agent_backend,
    checkpointer=BoundedMemorySaver(max_threads=200),
    system_prompt=SYSTEM_PROMPT,
)

app = FastAPI()
app.add_middleware(CredentialsMiddleware)


@app.post("/credentials/validate")
async def validate_provider_credentials():
    credentials = current_credentials.get()
    if credentials is None:
        return JSONResponse({"ok": False, "code": "invalid_keys"}, status_code=400)
    return await validate_credentials(credentials)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/deployment")
def deployment():
    # Build identity only: never return provider configuration or credentials.
    return {"config_version": PROVIDER_CONFIG_VERSION, "revision": _deployed_revision}


add_langgraph_fastapi_endpoint(
    app=app,
    agent=CredentialScopedAgent(
        name="sample_agent",
        description="Open Generative UI by CopilotKit — answers you can interact with",
        graph=agent,
    ),
    path="/",
)

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8123"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
