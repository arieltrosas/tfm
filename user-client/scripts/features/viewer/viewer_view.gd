@tool
class_name ViewerView extends PanelContainer


const PointGizmoScn: PackedScene = preload("res://scenes/gizmos/PointGizmo.tscn")
const BoxGizmoScn: PackedScene = preload("res://scenes/gizmos/BoxGizmo.tscn")

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
var _selections: Dictionary[String, SelectionGizmo] = {}

var _editing_gizmo: SelectionGizmo = null
var _editing_viewport_id: String = ""


func setup() -> void:
	AppEventBus.workspace_file_added.connect(_on_workspace_file_added)
	AppEventBus.workspace_file_removed.connect(_on_workspace_file_removed)
	AppEventBus.workspace_item_visibility_changed.connect(
		_on_workspace_item_visibility_changed
	)
	AppEventBus.selections_changed.connect(_on_selections_changed)


func generate_point_id() -> String:
	return _next_selection_id("Point")


func generate_box_id() -> String:
	return _next_selection_id("Box")


func add_point_selection(id: String, point: Vector3) -> void:
	var payload := {
		id: {
			"kind": "point",
			"point": _serialize_point(point),
		}
	}
	await BackendAPI.selection_add(payload)


func add_box_selection(id: String, aabb: AABB) -> void:
	var payload := {
		id: {
			"kind": "aabb",
			"aabb": _serialize_aabb(aabb),
		}
	}
	await BackendAPI.selection_add(payload)


func remove_selection(id: String) -> void:
	await BackendAPI.selection_remove([id])


func _ready() -> void:
	await get_tree().process_frame
	_sync_worlds()


func _sync_worlds() -> void:
	var world_3d := editor_world.get_world_3d()
	if world_3d == null:
		push_error("Editor world has no World3D")
		return

	for viewport in viewports.values():
		var _old_world_3d = viewport.world_3d
		viewport.world_3d = world_3d


func _on_workspace_file_added(file: String, source_path: String) -> void:
	if file in _objects:
		return

	var is_mesh: bool = await BackendAPI.geometry_mesh_supported(source_path)
	if not is_mesh:
		return

	var cache_dir := OS.get_cache_dir()
	var tmp_path := cache_dir.path_join(
		"tmp_mesh_%x.glb" % Time.get_ticks_msec()
	)

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


func _on_workspace_item_visibility_changed(
	file_id: StringName,
	visible: bool
) -> void:
	if file_id not in _objects:
		return
	_objects[file_id].visible = visible


func _on_selections_changed(selections: Dictionary) -> void:
	_rekey_renamed_gizmos(selections)
	_remove_deleted_gizmos(selections)
	_update_selection_gizmos(selections)


func _rekey_renamed_gizmos(selections: Dictionary) -> void:
	var removed: Array[String] = []
	var added: Array[String] = []
	for id in _selections:
		if id not in selections:
			removed.append(id)
	for id in selections:
		if id not in _selections:
			added.append(id)
	if removed.size() != 1 or added.size() != 1:
		return

	var old_id := removed[0]
	var new_id := added[0]
	var gizmo: SelectionGizmo = _selections[old_id]
	_selections.erase(old_id)
	_selections[new_id] = gizmo
	gizmo.name = "Gizmo_%s" % new_id


func _remove_deleted_gizmos(selections: Dictionary) -> void:
	for id in _selections.keys():
		if id in selections:
			continue

		var gizmo: SelectionGizmo = _selections[id]
		_selections.erase(id)
		gizmo.queue_free()

		if gizmo == _editing_gizmo:
			_cancel_gizmo_edit()


func _update_selection_gizmos(selections: Dictionary) -> void:
	for id in selections:
		var selection: Dictionary = selections[id]
		var gizmo := _get_or_create_gizmo(id, selection)

		if gizmo == null:
			continue

		_update_gizmo(gizmo, selection)


func _get_or_create_gizmo(
	id: String,
	selection: Dictionary
) -> SelectionGizmo:
	if id in _selections:
		return _selections[id]

	var gizmo := _create_gizmo(selection.get("kind", ""))
	if gizmo == null:
		return null

	gizmo.name = "Gizmo_%s" % id
	gizmo.gizmo_edited.connect(_on_gizmo_edited.bind(gizmo))
	editor_world.add_child(gizmo)
	_selections[id] = gizmo

	return gizmo


func _create_gizmo(kind: String) -> SelectionGizmo:
	match kind:
		"point":
			return PointGizmoScn.instantiate() as SelectionGizmo

		"aabb":
			return BoxGizmoScn.instantiate() as SelectionGizmo

		_:
			push_warning("Unknown selection gizmo kind: %s" % kind)
			return null


func _update_gizmo(gizmo: SelectionGizmo, selection: Dictionary) -> void:
	match selection.get("kind", ""):
		"point":
			_update_point_gizmo(gizmo as PointGizmo, selection)

		"aabb":
			_update_box_gizmo(gizmo as BoxGizmo, selection)


func _update_point_gizmo(
	gizmo: PointGizmo,
	selection: Dictionary
) -> void:
	if gizmo == null:
		return

	gizmo.set_point(_parse_point(selection.get("point", {})))


func _update_box_gizmo(
	gizmo: BoxGizmo,
	selection: Dictionary
) -> void:
	if gizmo == null:
		return

	gizmo.set_aabb(_parse_aabb(selection.get("aabb", {})))


func _on_gizmo_edited(gizmo: SelectionGizmo) -> void:
	var id := _id_for_gizmo(gizmo)
	if not id:
		return

	var selection := _selection_payload_from_gizmo(gizmo)
	if selection.is_empty():
		return

	await BackendAPI.selection_add({id: selection})


func _id_for_gizmo(gizmo: SelectionGizmo) -> String:
	for id in _selections:
		if _selections[id] == gizmo:
			return id
	return ""


func _selection_payload_from_gizmo(gizmo: SelectionGizmo) -> Dictionary:
	if gizmo is PointGizmo:
		return {
			"kind": "point",
			"point": _serialize_point((gizmo as PointGizmo).get_point()),
		}

	if gizmo is BoxGizmo:
		return {
			"kind": "aabb",
			"aabb": _serialize_aabb((gizmo as BoxGizmo).get_aabb()),
		}

	return {}


func _parse_point(data: Dictionary) -> Vector3:
	return Vector3(
		float(data.get("x", 0.0)),
		float(data.get("y", 0.0)),
		float(data.get("z", 0.0))
	)


func _parse_aabb(data: Dictionary) -> AABB:
	var aabb_position := Vector3(
		float(data.get("x", 0.0)),
		float(data.get("y", 0.0)),
		float(data.get("z", 0.0))
	)

	var aabb_size := Vector3(
		float(data.get("w", 0.0)),
		float(data.get("h", 0.0)),
		float(data.get("d", 0.0))
	)

	return AABB(aabb_position, aabb_size)


func _serialize_point(point: Vector3) -> Dictionary:
	return {
		"x": point.x,
		"y": point.y,
		"z": point.z,
	}


func _serialize_aabb(aabb: AABB) -> Dictionary:
	return {
		"x": aabb.position.x,
		"y": aabb.position.y,
		"z": aabb.position.z,
		"w": aabb.size.x,
		"h": aabb.size.y,
		"d": aabb.size.z,
	}


func _next_selection_id(prefix: String) -> String:
	var index := 0
	while true:
		var candidate := "%s%s" % [prefix, _selection_id_suffix(index)]
		if candidate not in _selections:
			return candidate
		index += 1
	return ""


func _selection_id_suffix(index: int) -> String:
	var suffix := ""
	var n := index
	while true:
		suffix = String.chr(65 + (n % 26)) + suffix
		@warning_ignore("integer_division")
		n = (n / 26) - 1
		if n < 0:
			break
	return suffix


func _is_gltf_file(file_id: StringName) -> bool:
	return str(file_id).get_extension().to_lower() in GLTF_EXTENSIONS


func _load_gltf(file_id: StringName, source_path: String) -> void:
	var gltf_document := GLTFDocument.new()
	var gltf_state := GLTFState.new()

	var error := gltf_document.append_from_file(source_path, gltf_state)
	if error != OK:
		printerr(
			"Couldn't load glTF scene for %s (error code: %s)."
			% [file_id, error_string(error)]
		)
		return

	var object := gltf_document.generate_scene(gltf_state)
	object.name = str(file_id)

	_objects[file_id] = object
	editor_world.add_child(object)
	AppEventBus.workspace_geometry_loaded.emit(file_id)


func _on_subviewport_gui_input(
	event: InputEvent,
	viewport_id: String
) -> void:
	var viewport: SubViewport = viewports.get(viewport_id)
	var camera: Camera3D = cameras.get(viewport_id)

	if viewport == null or camera == null:
		return

	camera.handle_input(event)

	if event is InputEventMouseButton:
		_handle_mouse_button(event, viewport_id, camera)
	elif event is InputEventMouseMotion:
		_handle_mouse_motion(event, viewport_id, camera)


func _handle_mouse_button(
	event: InputEventMouseButton,
	viewport_id: String,
	camera: Camera3D
) -> void:
	if event.button_index != MOUSE_BUTTON_LEFT:
		return

	if event.pressed:
		if _is_point_select_mode():
			var point = _pick_point_on_viewport(event.position, camera)
			if point != null:
				add_point_selection(generate_point_id(), point)
			return

		_begin_gizmo_edit(event.position, viewport_id, camera)
	else:
		if _is_point_select_mode():
			return

		_end_gizmo_edit(event.position, viewport_id, camera)


func _is_point_select_mode() -> bool:
	return %PointSelectButton.button_pressed


func _pick_point_on_viewport(mpos: Vector2, camera: Camera3D) -> Variant:
	var ray_origin: Vector3 = camera.project_ray_origin(mpos)
	var ray_direction: Vector3 = camera.project_ray_normal(mpos)
	
	var closest_hit: Variant = null
	var best_distance: float = INF
	
	for id in _objects:
		var object: Node3D = _objects[id]
		if object.visible:
			var hit: Variant = MeshIntersect.ray_intersect_scene(object, ray_origin, ray_direction)
			if not hit:
				continue
			
			if not closest_hit:
				closest_hit = hit
			else:
				var dist: float = camera.position.distance_squared_to((closest_hit as Vector3))
				if dist < best_distance:
					closest_hit = hit
					best_distance = dist
	
	return closest_hit


func _handle_mouse_motion(
	event: InputEventMouseMotion,
	viewport_id: String,
	camera: Camera3D
) -> void:
	if _editing_gizmo == null:
		return

	if _editing_viewport_id != viewport_id:
		return

	_editing_gizmo.edit(event.position, camera)


func _begin_gizmo_edit(
	mpos: Vector2,
	viewport_id: String,
	camera: Camera3D
) -> void:
	if _editing_gizmo != null:
		return

	for gizmo in _selections.values():
		gizmo.edit_begin(mpos, camera)

		if gizmo.is_editing():
			_editing_gizmo = gizmo
			_editing_viewport_id = viewport_id
			return


func _end_gizmo_edit(
	mpos: Vector2,
	viewport_id: String,
	camera: Camera3D
) -> void:
	if _editing_gizmo == null:
		return

	if _editing_viewport_id != viewport_id:
		return

	_editing_gizmo.edit_end(mpos, camera)
	_cancel_gizmo_edit()


func _cancel_gizmo_edit() -> void:
	_editing_gizmo = null
	_editing_viewport_id = ""


func _on_sub_viewport_container_a_gui_input(event: InputEvent) -> void:
	_on_subviewport_gui_input(event, "A")


func _on_sub_viewport_container_b_gui_input(event: InputEvent) -> void:
	_on_subviewport_gui_input(event, "B")


func _on_sub_viewport_container_c_gui_input(event: InputEvent) -> void:
	_on_subviewport_gui_input(event, "C")


func _on_box_select_button_pressed() -> void:
	add_box_selection(generate_box_id(), AABB(Vector3.ZERO, Vector3.ONE))
