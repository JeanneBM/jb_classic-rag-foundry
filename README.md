# Azure Foundry RAG Agent

A classic RAG (Retrieval-Augmented Generation) agent built with **Azure AI Foundry Agent Service** and **Azure AI Search Knowledge Base**, connected via the **Model Context Protocol (MCP)**.

The agent answers questions **only** using information from the connected knowledge base. It does not invent or hallucinate facts.

---

## Features

- Server-side prompt agent created with `AIProjectClient`
- Knowledge retrieval via MCP tool (`knowledge_base_retrieve`)
- Strict grounding – answers come exclusively from the knowledge base
- Source citations supported
- No manual tool approval required (`require_approval="never"`)

---

## Prerequisites

- Python 3.10+
- Azure subscription with:
  - Microsoft Foundry project
  - Azure AI Search service with a Knowledge Base
  - Deployed LLM (e.g. `gpt-4.1-mini`, `gpt-5-mini`)
- Azure CLI (`az login`)

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install "azure-ai-projects>=2.0.0" azure-identity python-dotenv openai
```

---

## Configuration

1. Copy `.env.example` to `.env`
2. Fill in the values:

```env
# Foundry project endpoint
PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>

# Knowledge Base MCP endpoint (Azure AI Search)
RAG_MCP_ENDPOINT=https://<search-service>.search.windows.net/knowledgebases/<kb-name>/mcp?api-version=2025-11-01-preview

# Project Connection name (RemoteTool type)
PROJECT_CONNECTION_NAME=my-kb-connection

# Optional
AGENT_NAME=RagAgent
MODEL_DEPLOYMENT=gpt-4.1-mini
```

### Where to find the values

| Variable | Location |
|----------|----------|
| `PROJECT_ENDPOINT` | Foundry Portal → Project → Overview / Endpoints |
| `RAG_MCP_ENDPOINT` | Azure AI Search → Knowledge bases → selected KB → MCP endpoint |
| `PROJECT_CONNECTION_NAME` | Foundry Portal → Project → Connections (RemoteTool) |
| `MODEL_DEPLOYMENT` | Foundry Portal → Models + endpoints |

---

## Create the agent

```bash
python create_rag_agent.py
```

This creates (or updates) an agent version named `RagAgent` with the MCP Knowledge Base tool attached.

---

## Chat with the agent

```bash
python chat.py
```

Or use the following code:

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
import os
from dotenv import load_dotenv

load_dotenv()

project = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

openai = project.get_openai_client()
conversation = openai.conversations.create()

response = openai.responses.create(
    conversation=conversation.id,
    input="Your question to the knowledge base...",
    extra_body={
        "agent_reference": {
            "name": os.environ.get("AGENT_NAME", "RagAgent"),
            "type": "agent_reference"
        }
    },
)

print(response.output_text)
```

---

## Project structure

```
.
├── .env                  # environment variables (do not commit)
├── .env.example
├── create_rag_agent.py   # creates the agent
├── chat.py               # sample conversation
├── README.md
├── GITHUB_ACTIONS.md
└── .github/
    └── workflows/
        └── ci.yml
```

---

## How it works

1. The agent receives a user question.
2. Based on its instructions, it calls the `knowledge_base_retrieve` MCP tool.
3. Azure AI Search Knowledge Base performs:
   - Query planning and decomposition
   - Hybrid / vector search
   - Semantic reranking
4. The agent generates a response **strictly** grounded in the retrieved sources and includes citations when possible.

---

## Important notes

- The agent never answers from the model's own knowledge – only from the Knowledge Base.
- If no relevant information is found, it replies with "I don't know".
- `require_approval="never"` means tool calls do not require manual approval.
- The Project Connection must use **Project Managed Identity** and have the **Search Index Data Reader** role on the Azure AI Search service.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Authentication failed | Run `az login` |
| Agent does not call the Knowledge Base | Check instructions and `allowed_tools=["knowledge_base_retrieve"]` |
| 403 / Access denied | Verify the project's Managed Identity has the correct role on Search |
| Connection not found | Ensure `PROJECT_CONNECTION_NAME` exists in the project |

---

## License

MIT
```
