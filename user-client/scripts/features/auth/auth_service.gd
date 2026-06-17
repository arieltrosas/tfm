class_name AuthService extends RefCounted


func connect_local_ollama() -> String:
	if await BackendAPI.connect_ollama("", ""):
		return "Successfully connected to local Ollama instance."
	return "Failed to connect to local Ollama instance."


func connect_provider(host: String, key: String) -> String:
	if host.is_empty():
		return await connect_local_ollama()

	if await BackendAPI.connect_openai(host, key):
		return "Successfully connected to OpenAI-compatible host."

	if await BackendAPI.connect_ollama("", ""):
		return "Failed to connect to OpenAI host. Fell back to local Ollama instance."

	return "Failed to connect to OpenAI host, and local Ollama fallback failed."
