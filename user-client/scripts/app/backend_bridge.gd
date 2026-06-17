class_name BackendBridge extends RefCounted

var _known_files: Array[StringName] = []
var _workspace_root: String = ""


func install() -> void:
	BackendAPI.remote_event.connect(_on_remote_event)
	BackendAPI.events_connected.connect(_on_events_connected)
	BackendAPI.events_disconnected.connect(_on_events_disconnected)


func _on_events_connected() -> void:
	AppEventBus.backend_events_connected.emit()


func _on_events_disconnected() -> void:
	AppEventBus.backend_events_disconnected.emit()


func _on_remote_event(event_type: String, payload: Dictionary) -> void:
	match event_type:
		"workspace.files_changed":
			_apply_workspace_files(payload.get("files", []))
		"volume.changed":
			AppEventBus.volume_changed.emit(BackendAPI.parse_aabb(payload.get("volume")))
		"app_state.changed":
			_workspace_root = payload.get("workspace_dir", _workspace_root)
			_apply_workspace_files(payload.get("files", []))
			AppEventBus.volume_changed.emit(BackendAPI.parse_aabb(payload.get("selected_volume")))


func _apply_workspace_files(files: Array) -> void:
	var next_files: Array[StringName] = []
	for file_name in files:
		next_files.append(StringName(str(file_name)))

	for file_id in _known_files:
		if file_id not in next_files:
			AppEventBus.workspace_file_removed.emit(file_id)

	for file_id in next_files:
		var path := _file_path(file_id)
		if file_id not in _known_files:
			AppEventBus.workspace_file_added.emit(file_id, path)

	_known_files = next_files
	AppEventBus.workspace_files_changed.emit(files.duplicate())


func _file_path(file_id: StringName) -> String:
	if _workspace_root.is_empty():
		return str(file_id)
	return _workspace_root.path_join(str(file_id))
