# Azure Foundry RAG Agent

Klasyczny agent RAG (Retrieval-Augmented Generation) zbudowany na **Azure AI Foundry Agent Service**, korzystający z **Azure AI Search Knowledge Base** jako źródła wiedzy, połączony przez **Model Context Protocol (MCP)**.

Agent odpowiada **wyłącznie** na podstawie informacji z podłączonej bazy wiedzy. Nie zmyśla faktów — jeśli czegoś nie ma w bazie, odpowiada "I don't know".

---

## Jak to działa (w skrócie)

```
Pytanie użytkownika
        │
        ▼
   Agent (Foundry)
        │  wywołuje narzędzie MCP: knowledge_base_retrieve
        ▼
Azure AI Search Knowledge Base
   - query planning / decomposition
   - hybrydowe / wektorowe wyszukiwanie
   - semantic reranking
        │
        ▼
Odpowiedź agenta z cytowaniami źródeł
```

**Ważne:** to repozytorium obsługuje tylko warstwę agenta i zapytań. **Nie tworzy ani nie zapełnia bazy wiedzy** — tę trzeba przygotować wcześniej w Azure AI Search (patrz krok 1 poniżej).

---

## Wymagania wstępne

- Python 3.10+
- Konto Azure z aktywną subskrypcją
- Azure CLI zainstalowane lokalnie
- Uprawnienia do tworzenia zasobów w Azure AI Foundry i Azure AI Search

---

## Krok 1 — Przygotuj bazę wiedzy w Azure AI Search (poza tym repo)

Zanim uruchomisz cokolwiek z tego projektu, musisz mieć gotową **Knowledge Base** w Azure AI Search. To jest osobny etap, wykonywany w Azure Portal (lub przez Azure CLI/SDK), i **ten projekt go nie automatyzuje**.

1. Utwórz usługę **Azure AI Search** (jeśli jeszcze jej nie masz), warstwa cenowa musi wspierać Knowledge Bases.
2. W usłudze utwórz zasób typu **Knowledge Base** i podepnij do niej źródło danych, np.:
   - Azure Blob Storage z dokumentami (PDF, DOCX, TXT, HTML itp.)
   - lub inny obsługiwany connector danych
3. Skonfiguruj wzbogacanie danych (skillset) — chunking, ekstrakcja tekstu, embeddingi — Azure AI Search robi to automatycznie po stronie usługi.
4. Poczekaj, aż indeksowanie się zakończy i baza wiedzy będzie gotowa do zapytań.
5. Zapisz sobie:
   - nazwę usługi Search (`<search-service>`)
   - nazwę Knowledge Base (`<kb-name>`)

> Formaty plików wejściowych i szczegóły indeksowania zależą od konfiguracji Twojej Knowledge Base w Azure AI Search — to ustawia się w samej usłudze, nie w tym repozytorium.

---

## Krok 2 — Przygotuj projekt w Azure AI Foundry

1. Utwórz projekt w **Microsoft Foundry** (Azure AI Foundry Portal).
2. W projekcie wdróż model LLM (np. `gpt-4.1-mini` lub `gpt-5-mini`).
3. W sekcji **Connections** utwórz połączenie typu **RemoteTool** do Twojej Knowledge Base w Azure AI Search.
4. Nadaj **Managed Identity projektu** rolę **Search Index Data Reader** na usłudze Azure AI Search — bez tego agent nie będzie miał dostępu do danych.

---

## Krok 3 — Zaloguj się do Azure lokalnie

```bash
az login
```

Projekt korzysta z `DefaultAzureCredential`, więc lokalne uwierzytelnienie przez Azure CLI wystarczy do testów.

---

## Krok 4 — Sklonuj repo i zainstaluj zależności

```bash
git clone https://github.com/JeanneBM/jb_classic-rag-foundry.git
cd jb_classic-rag-foundry

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

---

## Krok 5 — Skonfiguruj zmienne środowiskowe

1. Skopiuj plik przykładowy:

```bash
cp .env.example .env
```

2. Uzupełnij `.env` wartościami z Twojego środowiska Azure:

```
# Endpoint projektu Foundry
PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>

# Endpoint MCP Knowledge Base (Azure AI Search)
RAG_MCP_ENDPOINT=https://<search-service>.search.windows.net/knowledgebases/<kb-name>/mcp?api-version=2025-11-01-preview

# Nazwa Project Connection (typu RemoteTool)
PROJECT_CONNECTION_NAME=my-kb-connection

# Opcjonalne
AGENT_NAME=RagAgent
MODEL_DEPLOYMENT=gpt-4.1-mini
```

### Skąd wziąć poszczególne wartości

| Zmienna | Gdzie znaleźć |
|---|---|
| `PROJECT_ENDPOINT` | Foundry Portal → Project → Overview / Endpoints |
| `RAG_MCP_ENDPOINT` | Azure AI Search → Knowledge bases → wybrana KB → MCP endpoint |
| `PROJECT_CONNECTION_NAME` | Foundry Portal → Project → Connections (RemoteTool) |
| `MODEL_DEPLOYMENT` | Foundry Portal → Models + endpoints |

---

## Krok 6 — Utwórz agenta

```bash
python create_rag_agent.py
```

Ten skrypt tworzy (lub aktualizuje) agenta o nazwie z `AGENT_NAME` (domyślnie `RagAgent`) z podpiętym narzędziem MCP do Knowledge Base.

Jeśli w konsoli zobaczysz komunikat o brakujących zmiennych środowiskowych — wróć do kroku 5 i uzupełnij `.env`.

Po sukcesie zobaczysz:

```
Agent created successfully:
 ID      : ...
 Name    : RagAgent
 Version : ...
```

---

## Krok 7 — Porozmawiaj z agentem

```bash
python chat.py
```

Zadaj pytanie dotyczące treści z Twojej bazy wiedzy. Agent powinien odpowiedzieć z cytowaniem źródeł, a jeśli nie znajdzie odpowiedzi — odpowie "I don't know".

---

## (Opcjonalnie) Usunięcie agenta

Jeśli chcesz posprzątać po testach:

```bash
python delete_rag_agent.py
```

---

## CI/CD przez GitHub Actions (opcjonalnie)

Jeśli chcesz, żeby agent tworzył/aktualizował się automatycznie przy pushu na `main`, repo zawiera gotowy workflow (`.github/workflows/ci.yml`) korzystający z **OpenID Connect (OIDC)** — bez przechowywania sekretów Azure w repozytorium.

Wymaga to jednorazowej konfiguracji:

1. Utworzenia **App Registration** i **Service Principal** w Azure (`az ad app create`, `az ad sp create`).
2. Nadania ról: `Contributor` na resource group, oraz odpowiednich ról na projekcie Foundry i usłudze Azure AI Search (`Search Index Data Reader`).
3. Utworzenia **Federated Credential** wiążącego repo/branch z App Registration (bez sekretów).
4. Dodania w GitHub → Settings → Secrets and variables → Actions sekretów: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, a opcjonalnie też `PROJECT_ENDPOINT`, `RAG_MCP_ENDPOINT`, `PROJECT_CONNECTION_NAME` (jeśli workflow ma sam tworzyć agenta w CI).

Workflow ma dwa etapy: `lint` (Ruff) na każdym push/PR, oraz `deploy-agent` (uruchamia `create_rag_agent.py`) tylko na branchu `main`, z opcjonalną ochroną środowiska `production` (wymagani recenzenci).

Pełna instrukcja krok po kroku, w tym dokładne komendy `az` i troubleshooting dla OIDC, znajduje się w **[GITHUB_ACTIONS.md](./GITHUB_ACTIONS.md)**.

> To jest krok opcjonalny — do zwykłego, lokalnego uruchomienia agenta (Kroki 1–7 powyżej) nie jest potrzebny.

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---|---|
| Authentication failed | Uruchom `az login` ponownie |
| Agent nie wywołuje Knowledge Base | Sprawdź instrukcje agenta i `allowed_tools=["knowledge_base_retrieve"]` w `create_rag_agent.py` |
| 403 / Access denied | Sprawdź, czy Managed Identity projektu ma rolę Search Index Data Reader na usłudze Search |
| Connection not found | Upewnij się, że `PROJECT_CONNECTION_NAME` istnieje w projekcie Foundry i jest typu RemoteTool |
| Brak odpowiedzi z bazy wiedzy | Sprawdź, czy indeksowanie w Azure AI Search się zakończyło i KB zawiera dane |

---

## Struktura projektu

```
.
├── .env                  # zmienne środowiskowe (nie commitować)
├── .env.example
├── create_rag_agent.py   # tworzy/aktualizuje agenta
├── delete_rag_agent.py   # usuwa agenta
├── chat.py                # przykładowa rozmowa z agentem
├── requirements.txt
├── README.md
├── GITHUB_ACTIONS.md
└── .github/
    └── workflows/
        └── ci.yml
```

---

## Ważne uwagi

- Agent odpowiada wyłącznie na podstawie danych z Knowledge Base — nigdy z własnej wiedzy modelu.
- `require_approval="never"` oznacza, że wywołania narzędzia MCP nie wymagają ręcznego zatwierdzenia przy każdym pytaniu.
- Ten projekt **nie zajmuje się** tworzeniem, ładowaniem ani indeksowaniem dokumentów w Knowledge Base — to trzeba zrobić osobno w Azure AI Search (krok 1).

---

## Licencja

MIT
