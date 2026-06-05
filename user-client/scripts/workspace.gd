class_name Workspace extends PanelContainer

const ViewerObjectScn = preload("res://scenes/ViewerObject.tscn")
const WorkspaceItemScn = preload("res://scenes/ui/WorkspaceItem.tscn")

signal workspace_updated
signal item_added(file_id: StringName)
signal item_updated(file_id: StringName)
signal item_removed(file_id: StringName)
signal viewer_object_added(object: ViewerObject)
signal viewer_object_removed(object: ViewerObject)

var workspace: Dictionary[StringName, WorkspaceItem]
var viewer_objects: Dictionary[StringName, ViewerObject]


func _ready() -> void:
	%FileDialog.current_dir = OS.get_system_dir(OS.SYSTEM_DIR_DESKTOP)
	_update_workspace()


func _update_workspace() -> void:
	%WorkspaceRefreshTimer.stop()
	
	var ws_files := await BackendAPI.workspace_files()
	
	for file_id in workspace.keys():
		if file_id not in ws_files:
			_remove_item(file_id)
	
	for file_id in ws_files:
		if file_id not in workspace:
			_add_item(file_id)
		else:
			_update_item(file_id)
	
	workspace_updated.emit()
	%WorkspaceRefreshTimer.start()


func _add_item(file_id: StringName) -> void:
	if not file_id:
		return
	
	var item: WorkspaceItem = WorkspaceItemScn.instantiate()
	item.mesh_button_toggled.connect(_on_workspace_item_mesh_toggled.bind(file_id))
	item.cloud_button_toggled.connect(_on_workspace_item_cloud_toggled.bind(file_id))
	item.visible_button_toggled.connect(_on_workspace_item_visible_toggled.bind(file_id))
	
	item.file_name = ""
	workspace[file_id] = item
	
	%ItemList.add_child(item)
	
	_update_workspace()
	item_added.emit(file_id)


func _remove_item(file_id: StringName) -> void:
	if file_id not in workspace:
		return
	
	_remove_viewer_object(file_id)
	
	var item: WorkspaceItem = workspace[file_id]
	workspace.erase(file_id)
	%ItemList.remove_child(item)
	item.queue_free()
	
	_update_workspace()
	item_removed.emit(file_id)


func _update_item(file_id: StringName) -> void:
	if file_id not in workspace:
		return
	
	var item: WorkspaceItem = workspace[file_id]
	item.file_name = file_id
	
	item_updated.emit(file_id)


func _deselect_items() -> void:
	for file_id in workspace:
		workspace[file_id].selected = false


func _get_selected_items() -> Array[StringName]:
	return workspace.keys().filter(
		func(file_id: StringName): return workspace[file_id].selected
	)


func _add_viewer_object(file_id: StringName) -> void:
	if file_id in viewer_objects:
		return
	
	var ws_path: String = await BackendAPI.workspace()
	if not ws_path:
		return
	
	var path = ws_path.path_join(file_id)
	if not FileAccess.file_exists(path):
		return
	
	var object: ViewerObject = ViewerObjectScn.instantiate()
	object.source_path = path
	viewer_objects[file_id] = object
	viewer_object_added.emit(object)
	
	workspace[file_id].set_view_mode_toggles_visible(true)


func _remove_viewer_object(file_id: StringName) -> void:
	if file_id not in viewer_objects:
		return
	
	var object = viewer_objects[file_id]
	viewer_objects.erase(file_id)
	viewer_object_removed.emit(object)
	object.queue_free()
	
	workspace[file_id].set_view_mode_toggles_visible(false)


func _on_add_pressed() -> void:
	%FileDialog.file_mode = FileDialog.FILE_MODE_OPEN_FILES
	%FileDialog.popup_centered_clamped()


func _on_remove_pressed() -> void:
	var selected = _get_selected_items()
	for file_id in selected:
		await BackendAPI.workspace_remove(file_id)
		_remove_item(file_id)


func _on_workspace_refresh_timer_timeout() -> void:
	_update_workspace()


func _on_visualize_pressed() -> void:
	var selected = _get_selected_items()
	for file_id in selected:
		if file_id in viewer_objects:
			_remove_viewer_object(file_id)
		else:
			_add_viewer_object(file_id)
	_deselect_items()


func _on_workspace_item_mesh_toggled(toggled_on: bool, file_id: StringName) -> void:
	if not file_id in viewer_objects or not toggled_on:
		return
	viewer_objects[file_id].view_mode = ViewerObject.MESH


func _on_workspace_item_cloud_toggled(toggled_on: bool, file_id: StringName) -> void:
	if not file_id in viewer_objects or not toggled_on:
		return
	viewer_objects[file_id].view_mode = ViewerObject.POINT_CLOUD


func _on_workspace_item_visible_toggled(toggled_on: bool, file_id: StringName) -> void:
	if not file_id in viewer_objects:
		return
	viewer_objects[file_id].visible = toggled_on


func _on_save_pressed() -> void:
	for file_name in _get_selected_items():
		%FileDialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
		%FileDialog.current_file = file_name
		%FileDialog.popup_centered_clamped()
		
		var dst_path = await %FileDialog.file_selected
		BackendAPI.workspace_download(file_name, dst_path)


func _on_file_dialog_files_selected(paths: PackedStringArray) -> void:
	if %FileDialog.file_mode == FileDialog.FILE_MODE_SAVE_FILE:
		return
	for path in paths:
		var file_id: String = await BackendAPI.workspace_upload(path)
		_add_item(file_id)


func _on_item_added(file_id: StringName) -> void:
	if file_id.get_extension() == "ply":
		_add_viewer_object(file_id)
