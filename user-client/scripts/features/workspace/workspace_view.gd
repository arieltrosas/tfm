class_name WorkspaceView extends PanelContainer

const WorkspaceItemScn = preload("res://scenes/ui/WorkspaceItem.tscn")

var _service: WorkspaceService
var workspace: Dictionary[StringName, WorkspaceItem] = {}


func setup(service: WorkspaceService) -> void:
	_service = service
	AppEventBus.workspace_files_changed.connect(_on_workspace_files_changed)


func _ready() -> void:
	%FileDialog.current_dir = OS.get_system_dir(OS.SYSTEM_DIR_DESKTOP)


func _on_workspace_files_changed(files: Array) -> void:
	_sync_from_files(files)


func _sync_from_files(files: Array) -> void:
	var ws_files: Array[StringName] = []
	for file_name in files:
		ws_files.append(StringName(str(file_name)))

	for file_id in workspace.keys():
		if file_id not in ws_files:
			_remove_item(file_id)

	for file_id in ws_files:
		if file_id not in workspace:
			_add_item(file_id)
		else:
			_update_item(file_id)


func _add_item(file_id: StringName) -> void:
	if not file_id:
		return

	var item: WorkspaceItem = WorkspaceItemScn.instantiate()
	item.file_name = ""
	workspace[file_id] = item
	%ItemList.add_child(item)
	_update_item(file_id)


func _remove_item(file_id: StringName) -> void:
	if file_id not in workspace:
		return

	var item: WorkspaceItem = workspace[file_id]
	workspace.erase(file_id)
	%ItemList.remove_child(item)
	item.queue_free()


func _update_item(file_id: StringName) -> void:
	if file_id not in workspace:
		return
	workspace[file_id].file_name = file_id


func _get_selected_items() -> Array[StringName]:
	return workspace.keys().filter(
		func(file_id: StringName): return workspace[file_id].selected
	)


func _deselect_items() -> void:
	for file_id in workspace:
		workspace[file_id].selected = false


func _on_add_pressed() -> void:
	%FileDialog.file_mode = FileDialog.FILE_MODE_OPEN_FILES
	%FileDialog.popup_centered_clamped()


func _on_remove_pressed() -> void:
	await _service.remove_files(_get_selected_items())
	_deselect_items()


func _on_save_pressed() -> void:
	for file_name in _get_selected_items():
		%FileDialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
		%FileDialog.current_file = str(file_name)
		%FileDialog.popup_centered_clamped()
		var dst_path = await %FileDialog.file_selected
		_service.download_file(file_name, dst_path)


func _on_file_dialog_files_selected(paths: PackedStringArray) -> void:
	if %FileDialog.file_mode == FileDialog.FILE_MODE_SAVE_FILE:
		return
	await _service.upload_files(paths)
