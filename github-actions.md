# GitHub Actions Setup – Azure Foundry RAG Agent

This document explains how to configure **secure, passwordless** GitHub Actions for the Azure Foundry RAG Agent project using **OpenID Connect (OIDC)**.

No client secrets are stored in the repository.

---

## 1. Prerequisites

- Azure subscription with sufficient permissions (Owner or User Access Administrator)
- Azure CLI installed and logged in (`az login`)
- GitHub repository already created

---

## 2. Create App Registration + Federated Credential (one-time)

Run the following commands in your terminal:

```bash
# 1. Create App Registration
az ad app create --display-name "github-foundry-rag-agent"

# Note the "appId" from the output → this is your AZURE_CLIENT_ID

# 2. Create Service Principal
az ad sp create --id <APPLICATION_ID>

# 3. Assign required roles
# Example: Contributor on the resource group
az role assignment create \
  --assignee <APPLICATION_ID> \
  --role "Contributor" \
  --scope /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP>

# Also assign:
# - Foundry Project Manager (or equivalent) on the Foundry project
# - Search Index Data Reader on the Azure AI Search service

# 4. Create Federated Credential (no secrets!)
az ad app federated-credential create \
  --id <APPLICATION_ID> \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<GITHUB_OWNER>/<REPO_NAME>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

Replace:
- `<APPLICATION_ID>` with the appId from step 1
- `<GITHUB_OWNER>/<REPO_NAME>` with your repository (e.g. `janek/azure-foundry-rag-agent`)

### Optional: Additional Federated Credentials

You can create more credentials for other scenarios:

| Subject example | Use case |
|-----------------|----------|
| `repo:owner/repo:ref:refs/heads/main` | main branch |
| `repo:owner/repo:pull_request` | Pull requests |
| `repo:owner/repo:environment:production` | Environment protection |

---

## 3. Add GitHub Secrets

Go to your repository → **Settings → Secrets and variables → Actions** and create the following **Repository secrets**:

| Secret Name | Value |
|-------------|-------|
| `AZURE_CLIENT_ID` | Application (client) ID from App Registration |
| `AZURE_TENANT_ID` | Directory (tenant) ID |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID |

### Optional secrets (if the workflow creates/updates the agent)

| Secret Name | Value |
|-------------|-------|
| `PROJECT_ENDPOINT` | Foundry project endpoint |
| `RAG_MCP_ENDPOINT` | Knowledge Base MCP endpoint |
| `PROJECT_CONNECTION_NAME` | Name of the RemoteTool connection |

---

## 4. Workflow File

Create the file `.github/workflows/ci.yml` with the following content:

```yaml
name: CI - Azure Foundry RAG Agent

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write   # Required for OIDC
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install "azure-ai-projects>=2.0.0" azure-identity python-dotenv openai ruff

      - name: Lint with Ruff
        run: ruff check .

  deploy-agent:
    needs: lint
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production   # Optional: add required reviewers in GitHub Environments

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install "azure-ai-projects>=2.0.0" azure-identity python-dotenv openai

      - name: Create / Update RAG Agent
        env:
          PROJECT_ENDPOINT: ${{ secrets.PROJECT_ENDPOINT }}
          RAG_MCP_ENDPOINT: ${{ secrets.RAG_MCP_ENDPOINT }}
          PROJECT_CONNECTION_NAME: ${{ secrets.PROJECT_CONNECTION_NAME }}
          AGENT_NAME: RagAgent
          MODEL_DEPLOYMENT: gpt-4.1-mini
        run: python create_rag_agent.py
```

---

## 5. Recommended Extra Steps

### Environment Protection (Production)

1. Go to **Settings → Environments**
2. Create environment named `production`
3. Enable **Required reviewers**
4. Optionally restrict to the `main` branch

### Additional Federated Credential for PRs (optional)

```bash
az ad app federated-credential create \
  --id <APPLICATION_ID> \
  --parameters '{
    "name": "github-pull-request",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<GITHUB_OWNER>/<REPO_NAME>:pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

### Separate Lint-only Workflow for Pull Requests

You can keep the `deploy-agent` job only on `main` (as shown above) so pull requests only run linting.

---

## 6. Verification

1. Push the workflow file to the `main` branch
2. Go to the **Actions** tab in GitHub
3. The workflow should start automatically
4. Check the "Azure Login (OIDC)" step – it should succeed without any client secret

---

## 7. Troubleshooting

| Problem | Solution |
|---------|----------|
| `AADSTS700016` or similar | Federated credential subject does not match the repository/branch |
| `id-token` permission error | Make sure `permissions: id-token: write` is present |
| 403 Forbidden when creating agent | Service principal missing roles on Foundry project / Search |
| Login works but agent creation fails | Check that `PROJECT_ENDPOINT`, `RAG_MCP_ENDPOINT` and `PROJECT_CONNECTION_NAME` secrets are set |

---

## Security Notes

- OIDC is the recommended authentication method (no long-lived secrets)
- The federated credential is scoped to a specific repository and branch
- Use GitHub Environments + required reviewers for production deployments
- Prefer least-privilege roles on the Service Principal

---

## License

MIT
```
