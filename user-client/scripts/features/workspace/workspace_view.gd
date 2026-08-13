class_name WorkspaceView extends PanelContainer

const WorkspaceItemScn = preload("res://scenes/ui/WorkspaceItem.tscn")

var _service: WorkspaceService
var workspace: Dictionary[String, WorkspaceItem] = {}


func setup(service: WorkspaceService) -> void:
	_service = service
	AppEventBus.workspace_files_changed.connect(_on_workspace_files_changed)
	AppEventBus.workspace_geometry_loaded.connect(_on_workspace_geometry_loaded)


func _ready() -> void:
	%FileDialog.current_dir = OS.get_system_dir(OS.SYSTEM_DIR_DESKTOP)


func _on_workspace_files_changed(files: Array) -> void:
	_sync_from_files(files)


func _sync_from_files(files: Array) -> void:
	var ws_files: Array[StringName] = []
	for file_name in files:
		ws_files.append(StringName(str(file_name)))

	for file in workspace.keys():
		if file not in ws_files:
			_remove_item(file)

	for file in ws_files:
		if file not in workspace:
			_add_item(file)
		else:
			_update_item(file)


func _add_item(file: StringName) -> void:
	if not file:
		return

	var item: WorkspaceItem = WorkspaceItemScn.instantiate()
	item.file_name = ""
	item.visibility_toggled.connect(_on_item_visibility_toggled.bind(file))
	workspace[file] = item
	%ItemList.add_child(item)
	_update_item(file)


func _on_workspace_geometry_loaded(file: StringName) -> void:
	if file not in workspace:
		return
	workspace[file].enable_toggles(true)


func _on_item_visibility_toggled(visible: bool, file: StringName) -> void:
	AppEventBus.workspace_item_visibility_changed.emit(file, visible)


func _remove_item(file: StringName) -> void:
	if file not in workspace:
		return

	var item: WorkspaceItem = workspace[file]
	workspace.erase(file)
	%ItemList.remove_child(item)
	item.queue_free()


func _update_item(file: StringName) -> void:
	if file not in workspace:
		return
	workspace[file].file_name = file


func _get_selected_items() -> Array[String]:
	return workspace.keys().filter(
		func(file: StringName): return workspace[file].selected
	)


func _deselect_items() -> void:
	for file in workspace:
		workspace[file].selected = false


func _on_add_pressed() -> void:
	%FileDialog.file_mode = FileDialog.FILE_MODE_OPEN_FILES
	%FileDialog.popup_centered_clamped()


func _on_remove_pressed() -> void:
	await _service.remove_files(_get_selected_items())
	_deselect_items()


func _on_save_pressed() -> void:
	for file in _get_selected_items():
		%FileDialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
		%FileDialog.current_file = file
		%FileDialog.popup_centered_clamped()
		var dst_path = await %FileDialog.file_selected
		_service.download_file(file, dst_path)


func _on_file_dialog_files_selected(paths: PackedStringArray) -> void:
	if %FileDialog.file_mode == FileDialog.FILE_MODE_SAVE_FILE:
		return
	await _service.upload_files(paths)
