import requests


class AgentClient:
    """HTTP client for the Agent server.

    This module contains no GUI code. It is responsible only for talking to
    the FastAPI server and returning Python data to the caller.
    """

    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.conversation_id: str | None = None
        self.user: str | None = None

    def _post(self, endpoint: str, payload: dict) -> requests.Response:
        response = requests.post(
            f"{self.base_url}{endpoint}",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response

    def login(self, user: str) -> str | None:
        """Login an existing user.

        Returns the conversation id when the user exists.
        Returns None when the server returns no conversation id.
        """
        response = self._post("/login", {"user": user})
        conversation_id = response.json().get("conversation_id")

        if conversation_id:
            self.user = user
            self.conversation_id = conversation_id

        return conversation_id

    def register(self, user: str) -> str:
        """Register a user and store the returned conversation id."""
        response = self._post("/register", {"user": user})
        conversation_id = response.json().get("conversation_id")

        if not conversation_id:
            raise ValueError("Registration succeeded but no conversation_id was returned.")

        self.user = user
        self.conversation_id = conversation_id
        return conversation_id

    def send_message(self, user_input: str) -> dict:
        """Send one chat message using the current conversation."""
        if not user_input.strip():
            raise ValueError("Message cannot be empty.")

        payload = {"input": user_input}
        if self.conversation_id is not None:
            payload["conversation_id"] = self.conversation_id

        return self._post("/message", payload).json()

    def logout(self) -> None:
        """Clear only the local client session."""
        self.user = None
        self.conversation_id = None
