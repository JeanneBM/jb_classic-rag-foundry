import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
AGENT_NAME = os.environ.get("AGENT_NAME", "RagAgent")

# Opcjonalnie: numer wersji do usunięcia (np. "1", "2" ...)
# AGENT_VERSION = os.environ.get("AGENT_VERSION", "1")


def main() -> None:
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )

    # -------------------------------------------------------
    # OPCJA 1 – usuń TYLKO konkretną wersję agenta (aktywna)
    # -------------------------------------------------------
    AGENT_VERSION = os.environ.get("AGENT_VERSION", "1")

    result = project.agents.delete_version(
        agent_name=AGENT_NAME,
        agent_version=AGENT_VERSION,
    )
    print(f"Usunięto wersję {AGENT_VERSION} agenta '{AGENT_NAME}'.")
    print(result)

    # -------------------------------------------------------
    # OPCJA 2 – usuń CAŁEGO agenta (wszystkie wersje)
    # Odkomentuj poniższe linie i zakomentuj OPCJĘ 1, jeśli chcesz
    # -------------------------------------------------------
    # result = project.agents.delete(agent_name=AGENT_NAME)
    # print(f"Usunięto całego agenta '{AGENT_NAME}' (wszystkie wersje).")
    # print(result)


if __name__ == "__main__":
    main()
