# Azure Foundry RAG Agent

A classic RAG (Retrieval-Augmented Generation) agent built on **Azure AI Foundry Agent Service**, using an **Azure AI Search Knowledge Base** as its knowledge source, connected via the **Model Context Protocol (MCP)**.

The agent answers questions **only** using information from the connected knowledge base. It does not invent facts — if something isn't in the knowledge base, it replies "I don't know".

---

## How it works (in short)

```
User question
        │
        ▼
   Agent (Foundry)
        │  calls the MCP tool: knowledge_base_retrieve
        ▼
Azure AI Search Knowledge Base
   - query planning / decomposition
   - hybrid / vector search
   - semantic reranking
        │
        ▼
Agent's answer with source citations
```

**Important:** this repository only handles the agent and query layer. **It does not create or populate the knowledge base** — that needs to be prepared beforehand in Azure AI Search (see Step 1 below).


## What to expect (and its limitations)

In short: **yes, you can upload any documents to the Knowledge Base and ask any questions** — the agent will answer based on the content you upload, not from the model's general knowledge. If something isn't in the knowledge base, it should reply "I don't know" instead of making things up.

That said, it's worth understanding a few nuances so you don't get surprised by the quality of the answers:

- **Any question ≠ always an accurate answer.** Answer quality depends on whether the retrieval step (hybrid/vector search + semantic reranking) actually finds matching fragments. If your question uses very different wording than the documents, results may be weaker.
- **Documents are split into chunks before indexing.** If an answer requires combining information scattered across multiple parts of a document, the model may miss it, since it only sees selected chunks, not the whole document at once.
- **This is not 100% hallucination-proof.** The agent's instructions *ask* the model to stick to the sources and say "I don't know" when data is missing — that's prompt engineering, not a hard technical guarantee. A well-configured RAG setup significantly reduces the risk of making things up, but doesn't eliminate it entirely.
- **The topical scope is limited by the agent's own system prompt** (in `create_rag_agent.py`) — if you ask about something completely unrelated to the knowledge base content (e.g. general knowledge outside the documents), the agent should say "I don't know" rather than answer from the model's own knowledge.
---

## Prerequisites

- Python 3.10+
- An Azure account with an active subscription
- Azure CLI installed locally
- Permissions to create resources in Azure AI Foundry and Azure AI Search

---

## Step 1 — Prepare the Knowledge Base in Azure AI Search (outside this repo)

Before running anything from this project, you need a ready **Knowledge Base** in Azure AI Search. This is a separate step, done in the Azure Portal (or via Azure CLI/SDK), and **this project does not automate it**.

1. Create an **Azure AI Search** service (if you don't already have one); the pricing tier must support Knowledge Bases.
2. Within the service, create a **Knowledge Base** resource and connect a data source to it, e.g.:
   - Azure Blob Storage with documents (PDF, DOCX, TXT, HTML, etc.)
   - or another supported data connector
3. Configure data enrichment (skillset) — chunking, text extraction, embeddings — Azure AI Search handles this automatically on the service side.
4. Wait for indexing to complete and for the Knowledge Base to be ready for queries.
5. Note down:
   - the Search service name (`<search-service>`)
   - the Knowledge Base name (`<kb-name>`)

> Input file formats and indexing details depend on how your Knowledge Base is configured in Azure AI Search — this is set up in the service itself, not in this repository.

---

## Step 2 — Set up the Azure AI Foundry project

1. Create a project in **Microsoft Foundry** (Azure AI Foundry Portal).
2. Deploy an LLM in the project (e.g. `gpt-4.1-mini` or `gpt-5-mini`).
3. In the **Connections** section, create a **RemoteTool**-type connection to your Azure AI Search Knowledge Base.
4. Grant the project's **Managed Identity** the **Search Index Data Reader** role on the Azure AI Search service — without this, the agent won't be able to access the data.

---

## Step 3 — Log in to Azure locally

```bash
az login
```

The project uses `DefaultAzureCredential`, so local authentication via Azure CLI is enough for testing.

---

## Step 4 — Clone the repo and install dependencies

```bash
git clone https://github.com/JeanneBM/jb_classic-rag-foundry.git
cd jb_classic-rag-foundry

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

---

## Step 5 — Configure environment variables

1. Copy the example file:

```bash
cp .env.example .env
```

2. Fill in `.env` with values from your Azure environment:

```
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

### Where to find each value

| Variable | Location |
|---|---|
| `PROJECT_ENDPOINT` | Foundry Portal → Project → Overview / Endpoints |
| `RAG_MCP_ENDPOINT` | Azure AI Search → Knowledge bases → selected KB → MCP endpoint |
| `PROJECT_CONNECTION_NAME` | Foundry Portal → Project → Connections (RemoteTool) |
| `MODEL_DEPLOYMENT` | Foundry Portal → Models + endpoints |

---

## Step 6 — Create the agent

```bash
python create_rag_agent.py
```

This script creates (or updates) an agent named as per `AGENT_NAME` (default `RagAgent`) with the MCP Knowledge Base tool attached.

If you see a message about missing environment variables in the console — go back to Step 5 and complete `.env`.

On success you'll see:

```
Agent created successfully:
 ID      : ...
 Name    : RagAgent
 Version : ...
```

---

## Step 7 — Chat with the agent

```bash
python chat.py
```

Ask a question related to the content in your knowledge base. The agent should answer with source citations, or reply "I don't know" if it can't find an answer.

---

## (Optional) Delete the agent

To clean up after testing:

```bash
python delete_rag_agent.py
```

---

## CI/CD via GitHub Actions (optional)

If you want the agent to be created/updated automatically on every push to `main`, the repo includes a ready-made workflow (`.github/workflows/ci.yml`) using **OpenID Connect (OIDC)** — no Azure secrets stored in the repository.

This requires a one-time setup:

1. Create an **App Registration** and **Service Principal** in Azure (`az ad app create`, `az ad sp create`).
2. Grant roles: `Contributor` on the resource group, plus the appropriate roles on the Foundry project and the Azure AI Search service (`Search Index Data Reader`).
3. Create a **Federated Credential** linking the repo/branch to the App Registration (no secrets involved).
4. In GitHub → Settings → Secrets and variables → Actions, add: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, and optionally `PROJECT_ENDPOINT`, `RAG_MCP_ENDPOINT`, `PROJECT_CONNECTION_NAME` (if the workflow should create the agent itself in CI).

The workflow has two stages: `lint` (Ruff) on every push/PR, and `deploy-agent` (runs `create_rag_agent.py`) only on the `main` branch, with optional `production` environment protection (required reviewers).

Full step-by-step instructions, including exact `az` commands and OIDC troubleshooting, are in **[GITHUB_ACTIONS.md](./GITHUB_ACTIONS.md)**.

> This step is optional — it is not needed for local usage (Steps 1–7 above).

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Authentication failed | Run `az login` again |
| Agent doesn't call the Knowledge Base | Check the agent's instructions and `allowed_tools=["knowledge_base_retrieve"]` in `create_rag_agent.py` |
| 403 / Access denied | Verify the project's Managed Identity has the Search Index Data Reader role on the Search service |
| Connection not found | Make sure `PROJECT_CONNECTION_NAME` exists in the Foundry project and is of type RemoteTool |
| No response from the knowledge base | Check whether indexing in Azure AI Search has completed and the KB contains data |

---

## Project structure

```
.
├── .env                  # environment variables (do not commit)
├── .env.example
├── create_rag_agent.py   # creates/updates the agent
├── delete_rag_agent.py   # deletes the agent
├── chat.py                # sample conversation with the agent
├── requirements.txt
├── README.md
├── GITHUB_ACTIONS.md
└── .github/
    └── workflows/
        └── ci.yml
```

---

## Important notes

- The agent answers exclusively based on data from the Knowledge Base — never from the model's own knowledge.
- `require_approval="never"` means MCP tool calls don't require manual approval on every question.
- This project **does not handle** creating, uploading, or indexing documents in the Knowledge Base — that must be done separately in Azure AI Search (Step 1).

---

## License

MIT
