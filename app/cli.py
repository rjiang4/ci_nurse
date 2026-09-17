from client import AgentClient
from config import DEFAULT_SERVER_URL


def login(client: AgentClient) -> str:
    user = input("Username: ").strip()

    if not user:
        raise ValueError("Username cannot be empty.")

    conversation_id = client.login(user)

    if conversation_id:
        print(f"Logged in as {user}")
        return conversation_id

    register = input(
        f'User "{user}" was not found. Register? (y/n): '
    ).strip().lower()

    if register != "y":
        raise ValueError("Login cancelled.")

    conversation_id = client.register(user)
    print(f"Registered and logged in as {user}")

    return conversation_id


def main():
    server_url = input(
        f"Server URL [{DEFAULT_SERVER_URL}]: "
    ).strip()

    if not server_url:
        server_url = DEFAULT_SERVER_URL

    client = AgentClient(server_url)

    try:
        login(client)

        print()
        print("CI Nurse CLI")
        print("Type 'exit' or 'quit' to leave.")
        print()

        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in {"exit", "quit"}:
                    print("Goodbye!")
                    break

                data = client.send_message(user_input)
                output = data.get("output", "")

                print()
                print(f"CI Nurse: {output}")
                print()

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break

    finally:
        client.logout()


if __name__ == "__main__":
    main()
