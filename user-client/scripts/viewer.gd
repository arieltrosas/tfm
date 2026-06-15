@tool
class_name Viewer extends PanelContainer


@onready var editor_world: Node3D = %EditorWorld

@onready var viewports: Dictionary[String, SubViewport] = {
	"A": %SubViewportA,
	"B": %SubViewportB,
	"C": %SubViewportC
}

@onready var cameras: Dictionary[String, Camera3D] = {
	"A": %CameraA,
	"B": %CameraB,
	"C": %CameraC
}

@onready var point_size: float = %PointSizeSlider.value:
	set = set_point_size


var viewer_objects: Array[ViewerObject] = []
var _is_lmb_down: bool = false
var _updating_from_backend: bool = false


func _ready() -> void:
	BackendAPI.backend_ready.connect(BackendAPI.volume_set.bind(%VolumeGizmo.box))
	BackendAPI.volume_changed.connect(_on_volume_changed)
	BackendAPI.app_state_changed.connect(_on_app_state_changed)
	await get_tree().process_frame
	_sync_worlds()
	_update_objects()


func _sync_worlds() -> void:
	var world_3d := editor_world.get_world_3d()
	if world_3d == null:
		push_error("Editor world has no World3D")
		return

	for vp in viewports.values():
		var _old_world = vp.world_3d # this avoids a godot memory management bug, nothing important, but suppressed the error
		vp.world_3d = world_3d


func _on_volume_changed(volume: Variant) -> void:
	_apply_volume_from_backend(volume)


func _on_app_state_changed(state: Dictionary) -> void:
	_apply_volume_from_backend(_parse_volume_from_state(state))


func _parse_volume_from_state(state: Dictionary) -> Variant:
	return BackendAPI.parse_aabb(state.get("selected_volume"))


func _apply_volume_from_backend(volume: Variant) -> void:
	if %VolumeGizmo.is_dragging():
		return

	_updating_from_backend = true

	if volume is AABB and not %VolumeGizmo.box.is_equal_approx(volume):
		%VolumeGizmo.box = volume

	_updating_from_backend = false


func add_object(object: ViewerObject) -> void:
	if object in viewer_objects:
		return

	viewer_objects.append(object)
	editor_world.add_child(object)
	_update_objects()


func remove_object(object: ViewerObject) -> void:
	if object not in viewer_objects:
		return

	viewer_objects.erase(object)
	if object.get_parent() == editor_world:
		editor_world.remove_child(object)


func _update_objects() -> void:
	for object in viewer_objects:
		object.set_point_size(point_size)
		object.update_object()


func set_point_size(value: float) -> void:
	point_size = value
	_update_objects()


func _on_point_size_slider_value_changed(value: float) -> void:
	set_point_size(value)


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
	if _updating_from_backend:
		return

	%VolumeGizmo.visible = toggled_on
	%VolumeGizmo.disabled = not toggled_on


func _on_volume_gizmo_volume_changed(volume: AABB) -> void:
	if _updating_from_backend:
		return

	await BackendAPI.volume_set(volume)
