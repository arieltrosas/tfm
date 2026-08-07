@tool
class_name ViewerView extends PanelContainer

const GLTF_EXTENSIONS: Array[String] = ["glb", "gltf"]

@onready var editor_world: Node3D = %EditorWorld

@onready var viewports: Dictionary[String, SubViewport] = {
	"A": %SubViewportA,
	"B": %SubViewportB,
	"C": %SubViewportC,
}

@onready var cameras: Dictionary[String, Camera3D] = {
	"A": %CameraA,
	"B": %CameraB,
	"C": %CameraC,
}

var _objects: Dictionary[String, Node3D] = {}
var _is_lmb_down: bool = false


func setup() -> void:
	AppEventBus.workspace_file_added.connect(_on_workspace_file_added)
	AppEventBus.workspace_file_removed.connect(_on_workspace_file_removed)


func get_gizmo_box() -> AABB:
	return %VolumeGizmo.box


func _ready() -> void:
	await get_tree().process_frame
	_sync_worlds()


func _sync_worlds() -> void:
	var world_3d := editor_world.get_world_3d()
	if world_3d == null:
		push_error("Editor world has no World3D")
		return
	for vp in viewports.values():
		var _old_world_3d = vp.world_3d # this avoids a bug in godot's pointer handling
		vp.world_3d = world_3d


func _on_workspace_file_added(file: String, source_path: String) -> void:
	if file in _objects:
		return
	
	var is_mesh: bool = await BackendAPI.geometry_mesh_supported(source_path)
	
	if is_mesh:
		var cache_dir := OS.get_cache_dir()
		var tmp_path := cache_dir.path_join("tmp_mesh_%x.glb" % Time.get_ticks_msec())
		await BackendAPI.geometry_mesh_convert(source_path, tmp_path)
		_load_gltf(file, tmp_path)
		DirAccess.remove_absolute(tmp_path)


func _on_workspace_file_removed(file_id: StringName) -> void:
	if file_id not in _objects:
		return
	var object: Node3D = _objects[file_id]
	_objects.erase(file_id)
	if object.get_parent() == editor_world:
		editor_world.remove_child(object)
	object.queue_free()


func _is_gltf_file(file_id: StringName) -> bool:
	return str(file_id).get_extension().to_lower() in GLTF_EXTENSIONS


func _load_gltf(file_id: StringName, source_path: String) -> void:
	var gltf_document := GLTFDocument.new()
	var gltf_state := GLTFState.new()
	var error := gltf_document.append_from_file(source_path, gltf_state)
	if error != OK:
		printerr("Couldn't load glTF scene for %s (error code: %s)." % [file_id, error_string(error)])
		return

	var object := gltf_document.generate_scene(gltf_state)
	object.name = str(file_id)
	_objects[file_id] = object
	editor_world.add_child(object)


func _on_subviewport_gui_input(event: InputEvent, viewport_id: String) -> void:
	var viewport: SubViewport = viewports.get(viewport_id, null)
	var camera: Camera3D = cameras.get(viewport_id, null)
	if viewport == null or camera == null:
		return
	camera.handle_editor_input(event)
	if not %VolumeGizmo.disabled:
		_handle_gizmo_input(event, camera)


func _handle_gizmo_input(event: InputEvent, camera: Camera3D) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if _is_lmb_down and not event.pressed:
				%VolumeGizmo.end_drag()
			_is_lmb_down = event.pressed
			if event.pressed:
				%VolumeGizmo.try_start_drag(event.position, camera)
	elif event is InputEventMouseMotion:
		if _is_lmb_down and %VolumeGizmo.is_dragging():
			%VolumeGizmo.update_drag(event.position, camera)


func _on_sub_viewport_container_a_gui_input(event: InputEvent) -> void:
	_on_subviewport_gui_input(event, "A")


func _on_sub_viewport_container_b_gui_input(event: InputEvent) -> void:
	_on_subviewport_gui_input(event, "B")


func _on_sub_viewport_container_c_gui_input(event: InputEvent) -> void:
	_on_subviewport_gui_input(event, "C")


func _on_volume_select_toggle_toggled(toggled_on: bool) -> void:
	%VolumeGizmo.visible = toggled_on
	%VolumeGizmo.disabled = not toggled_on


func _on_volume_gizmo_volume_changed(_volume: AABB) -> void:
	pass
