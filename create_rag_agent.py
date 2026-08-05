import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
RAG_MCP_ENDPOINT = os.environ["RAG_MCP_ENDPOINT"]
PROJECT_CONNECTION_NAME = os.environ["PROJECT_CONNECTION_NAME"]
AGENT_NAME = os.environ.get("AGENT_NAME", "RagAgent")
MODEL_DEPLOYMENT = os.environ.get("MODEL_DEPLOYMENT", "gpt-4.1-mini")


def main() -> None:
    credential = DefaultAzureCredential()
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential,
    )

    # MCP tool pointing to the Knowledge Base (classic RAG)
    mcp_tool = MCPTool(
        server_label="KnowledgeBase",
        server_url=RAG_MCP_ENDPOINT,
        require_approval="never",
        allowed_tools=["knowledge_base_retrieve"],
        project_connection_id=PROJECT_CONNECTION_NAME,
    )

    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT,
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
