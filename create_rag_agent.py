"""Create or update the Azure Foundry RAG agent with Knowledge Base MCP tool."""

from __future__ import annotations

import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV = (
    "PROJECT_ENDPOINT",
    "RAG_MCP_ENDPOINT",
    "PROJECT_CONNECTION_NAME",
)


def _require_env() -> dict[str, str]:
    missing = [key for key in REQUIRED_ENV if not os.getenv(key)]
    if missing:
        print(
            "Missing required environment variables:\n  - "
            + "\n  - ".join(missing)
            + "\n\nCopy .env.example to .env and fill in the values.",
            file=sys.stderr,
        )
        sys.exit(1)

    return {
        "project_endpoint": os.environ["PROJECT_ENDPOINT"],
        "rag_mcp_endpoint": os.environ["RAG_MCP_ENDPOINT"],
        "project_connection_name": os.environ["PROJECT_CONNECTION_NAME"],
        "agent_name": os.environ.get("AGENT_NAME", "RagAgent"),
        "model_deployment": os.environ.get("MODEL_DEPLOYMENT", "gpt-4.1-mini"),
    }


def main() -> None:
    cfg = _require_env()

    credential = DefaultAzureCredential()
    project = AIProjectClient(
        endpoint=cfg["project_endpoint"],
        credential=credential,
    )

    mcp_tool = MCPTool(
        server_label="KnowledgeBase",
        server_url=cfg["rag_mcp_endpoint"],
        require_approval="never",
        allowed_tools=["knowledge_base_retrieve"],
        project_connection_id=cfg["project_connection_name"],
    )

    agent = project.agents.create_version(
        agent_name=cfg["agent_name"],
        definition=PromptAgentDefinition(
            model=cfg["model_deployment"],
            instructions=(
                "You are a helpful assistant that answers questions using only "
                "the connected knowledge base.\n"
                "Always use the knowledge_base_retrieve tool.\n"
                "Do not invent information that is not present in the sources.\n"
                "If you cannot find the answer in the knowledge base, reply with "
                '"I don\'t know".\n'
                "Include source citations whenever possible."
            ),
            tools=[mcp_tool],
        ),
    )

    print("Agent created successfully:")
    print(f"  ID      : {agent.id}")
    print(f"  Name    : {agent.name}")
    print(f"  Version : {agent.version}")


if __name__ == "__main__":
    main()
