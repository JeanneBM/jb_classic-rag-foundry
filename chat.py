import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
AGENT_NAME = os.environ.get("AGENT_NAME", "RagAgent")


def main() -> None:
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )

    openai = project.get_openai_client()

    # Create a new conversation
    conversation = openai.conversations.create()
    print(f"Conversation created: {conversation.id}")
    print("Type your question (or 'exit' to quit)\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("Bye!")
            break

        response = openai.responses.create(
            conversation=conversation.id,
            input=user_input,
            extra_body={
                "agent_reference": {
                    "name": AGENT_NAME,
                    "type": "agent_reference",
                }
            },
        )

        print(f"\nAgent: {response.output_text}\n")


if __name__ == "__main__":
    main()
