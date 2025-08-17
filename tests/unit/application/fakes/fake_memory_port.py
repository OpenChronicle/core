class FakeMemoryPort:
    def __init__(self):
        self._store = {}

    def get_session_memory(self, session_id):
        return self._store.get(session_id, {"facts": []})

    def save_memory(self, session_id, state):
        self._store[session_id] = state
        return True
