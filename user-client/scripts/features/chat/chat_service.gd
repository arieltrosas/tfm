class_name ChatService extends RefCounted

var available_models: Array[String] = []


func setup() -> void:
	pass


func send_message(text: String) -> String:
	var response := await BackendAPI.chat(text)
	AppEventBus.chat_response_received.emit(response)
	return response


func set_model(model_name: String) -> bool:
	return await BackendAPI.model_set(model_name)


func refresh_models() -> void:
	await _refresh_models()


func get_current_model_name() -> String:
	return await BackendAPI.model()


func _refresh_models() -> void:
	var new_models: Array[String] = []
	for model in await BackendAPI.model_list():
		new_models.append(str(model))

	if _are_arrays_equal(available_models, new_models):
		return

	available_models = new_models
	AppEventBus.models_changed.emit(available_models.duplicate())


func _are_arrays_equal(a: Array[String], b: Array[String]) -> bool:
	if a.size() != b.size():
		return false
	for i in range(a.size()):
		if a[i] != b[i]:
			return false
	return true
