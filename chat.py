"""Interactive chat with the Azure Foundry RAG agent."""

from __future__ import annotations

import os
import sys

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


def _require_env() -> tuple[str, str]:
    endpoint = os.getenv("PROJECT_ENDPOINT")
    if not endpoint:
        print(
            "Missing PROJECT_ENDPOINT.\n"
            "Copy .env.example to .env and fill in the values.",
            file=sys.stderr,
        )
        sys.exit(1)

    agent_name = os.environ.get("AGENT_NAME", "RagAgent")
    return endpoint, agent_name


def main() -> None:
    project_endpoint, agent_name = _require_env()

    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )
    openai = project.get_openai_client()

    conversation = openai.conversations.create()
    print(f"Conversation created: {conversation.id}")
    print("Type your question (or 'exit' / 'quit' / 'q' to quit)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("Bye!")
            break

        try:
            response = openai.responses.create(
                conversation=conversation.id,
                input=user_input,
                extra_body={
                    "agent_reference": {
                        "name": agent_name,
                        "type": "agent_reference",
                    }
                },
            )
            print(f"\nAgent: {response.output_text}\n")
        except Exception as exc:  # noqa: BLE001 – surface Azure/network errors clearly
            print(f"\nError: {exc}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
