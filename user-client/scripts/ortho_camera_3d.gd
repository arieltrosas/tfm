class_name EditorCameraOrtho extends Camera3D

const ORTHO_DISTANCE: float = 1000.0

enum View { FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM }

const VIEW_FRONT = View.FRONT
const VIEW_BACK = View.BACK
const VIEW_LEFT = View.LEFT
const VIEW_RIGHT = View.RIGHT
const VIEW_TOP = View.TOP
const VIEW_BOTTOM = View.BOTTOM

@export var view: View = VIEW_FRONT: set = _set_view

@export_category("Movement Speeds")
const base_pan_speed: float = 0.005
@export_range(0.1, 2.0) var pan_speed: float = 0.5
@export_range(0.1, 2.0) var zoom_speed: float = 1.0

@export_category("Limits")
@export var min_size: float = 1e-5
@export var max_size: float = 1e5

var _is_mmb_down: bool = false

func _ready() -> void:
	projection = Camera3D.PROJECTION_ORTHOGONAL

## Input
func handle_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		match event.button_index:
			MOUSE_BUTTON_MIDDLE:
				_is_mmb_down = event.pressed
			MOUSE_BUTTON_WHEEL_UP:
				if event.pressed:
					zoom(-1.0)
			MOUSE_BUTTON_WHEEL_DOWN:
				if event.pressed:
					zoom(1.0)
	elif event is InputEventMouseMotion:
		if _is_mmb_down:
			pan(event.relative)
	elif event is InputEventKey:
		match event.keycode:
			KEY_0:
				view = VIEW_FRONT
			KEY_1:
				view = VIEW_BACK
			KEY_2:
				view = VIEW_LEFT
			KEY_3:
				view = VIEW_RIGHT
			KEY_4:
				view = VIEW_TOP
			KEY_5:
				view = VIEW_BOTTOM

## Pans the camera across its viewing plane
func pan(relative_mouse: Vector2) -> void:
	var right: Vector3 = global_transform.basis.x
	var up: Vector3 = global_transform.basis.y
	
	var dynamic_speed: float = base_pan_speed * pan_speed * size
	
	global_position += right * -relative_mouse.x * dynamic_speed
	global_position += up * relative_mouse.y * dynamic_speed

## Zooms an orthogonal view by expanding or shrinking the size of the render frame
func zoom(direction_amount: float) -> void:
	var dynamic_zoom_delta: float = direction_amount * zoom_speed * (size * 0.1)
	
	size += dynamic_zoom_delta
	size = clamp(size, min_size, max_size)

## Snaps the ortho camera to a fixed orientation (e.g. Top, Side, Front)
func snap_to_orientation(target_rotation: Vector3) -> void:
	rotation = target_rotation
	global_position = Vector3.ZERO + (global_transform.basis.z * ORTHO_DISTANCE)


func _set_view(value: View) -> void:
	view = value
	
	if not is_inside_tree():
		await ready
	
	match view:
		VIEW_FRONT:
			snap_to_orientation(Vector3(0, 0, 0))
		VIEW_BACK:
			snap_to_orientation(Vector3(0, deg_to_rad(180), 0))
		VIEW_LEFT:
			snap_to_orientation(Vector3(0, deg_to_rad(-90), 0))
		VIEW_RIGHT:
			snap_to_orientation(Vector3(0, deg_to_rad(90), 0))
		VIEW_TOP:
			snap_to_orientation(Vector3(deg_to_rad(-90), 0, 0))
		VIEW_BOTTOM:
			snap_to_orientation(Vector3(deg_to_rad(90), 0, 0))
