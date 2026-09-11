import requests

#url = "http://localhost:8000"
url = "http://10.246.51.38:8080"

def login():

    user = input("Enter your username: ")
    payload = {"user": user}
    response = requests.post(
        f"{url}/login",
        json=payload
    )
    response.raise_for_status()
    conversation_id = response.json().get("conversation_id")
    if not conversation_id:
        if input(f"Register for {user}? (y/n): ").lower() != "y":
            raise ValueError("Login failed: No User Found.")
        
        response = requests.post(
            f"{url}/register",
            json=payload
        )
        response.raise_for_status()
        conversation_id = response.json().get("conversation_id")

    return conversation_id

def send_message(user_input: str, conversation_id: str = None):

    payload = {"input": user_input}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    response = requests.post(f"{url}/message", json=payload)
    response.raise_for_status()
    return response.json()

def main():

    conversation_id = login()

    while True:
        try:
            user_input = input("\nYou: ")
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print("GoodBye!")
                break
        except KeyboardInterrupt:
            print("\nGoodBye!")
            break

        data = send_message(user_input, conversation_id)

        print(f"\nAgent: {data.get('output')}.")

if __name__ == "__main__":
    main()

