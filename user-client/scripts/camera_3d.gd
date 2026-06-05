class_name EditorCamera extends Camera3D

const RADS_PER_PIXEL: float = PI / 4000.0
const BASE_SENSITIVITY: float = 1.0 / 7.5
const ELEVATION_LIMIT: float = PI * 0.5 * (1.0 - 1e-5)
const ZOOM_FACTOR: float = 1e-1

var azimuth: float = 0.0
var elevation: float = 0.0:
	set(value):
		elevation = clampf(value, -ELEVATION_LIMIT, ELEVATION_LIMIT)
var distance: float = 0.0:
	set(value):
		distance = abs(value)


func _ready() -> void:
	azimuth = Vector3(position.x, 0.0, position.y).signed_angle_to(Vector3.FORWARD, Vector3.UP)
	elevation = Vector3(0.0, position.y, 0.0).signed_angle_to(Vector3.FORWARD, Vector3.RIGHT)
	distance = position.length()


func _process(_delta: float) -> void:
	var p: Vector3 = Vector3(0, 0, distance)
	p = p.rotated(Vector3.RIGHT, elevation)
	p = p.rotated(Vector3.UP, azimuth)
	look_at_from_position(p, Vector3(0,0,0))


func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		var e := event as InputEventMouseMotion
		if e.button_mask & MOUSE_BUTTON_MASK_MIDDLE:
			var v: Vector2 = e.screen_velocity * RADS_PER_PIXEL * BASE_SENSITIVITY
			azimuth -= v.x
			elevation -= v.y
	
	if event is InputEventMouseButton:
		var e := event as InputEventMouseButton
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = distance * (1.0 + ZOOM_FACTOR)
		if e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = distance * (1.0 - ZOOM_FACTOR)
