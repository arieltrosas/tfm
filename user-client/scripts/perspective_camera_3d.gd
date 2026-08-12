class_name EditorCameraPerspective extends Camera3D

@export_category("Movement Speeds")
const minimum_orbit_radius: float = 1e-5
const base_orbit_speed: float = 0.005
@export_range(0.1, 2.0) var orbit_speed: float = 1.0
const base_pan_speed: float = 0.001
@export_range(0.1, 2.0) var pan_speed: float = 1.0
const base_zoom_step: float = 0.1
@export_range(0.1, 2.0) var zoom_speed: float = 1

# Track internal rotation to completely avoid gimbal lock
var yaw: float = 0.0
var pitch: float = 0.0

# State tracking variables for input
var _is_mmb_down: bool = false
var _is_rmb_down: bool = false

## The 3D point the camera rotates around. 
var orbit_target: Vector3 = Vector3.ZERO 

func _ready() -> void:
	projection = Camera3D.PROJECTION_PERSPECTIVE
	yaw = rotation.y
	pitch = rotation.x

## Input
func handle_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		match event.button_index:
			MOUSE_BUTTON_MIDDLE:
				_is_mmb_down = event.pressed
			MOUSE_BUTTON_RIGHT:
				_is_rmb_down = event.pressed
			MOUSE_BUTTON_WHEEL_UP:
				if event.pressed:
					zoom(-1.0)
			MOUSE_BUTTON_WHEEL_DOWN:
				if event.pressed:
					zoom(1.0)
	elif event is InputEventMouseMotion:
		if _is_mmb_down:
			if Input.is_physical_key_pressed(KEY_SHIFT):
				var old_pos = global_position
				pan(event.relative)
				var travel_vector = global_position - old_pos
				orbit_target += travel_vector # Keeps orbit feeling seamless after panning
			else:
				orbit(event.relative, orbit_target)
		elif _is_rmb_down:
			rotate_free(event.relative)

## Translates the camera along its local X and Y axes, scaled by target distance
func pan(relative_mouse: Vector2) -> void:
	var right: Vector3 = global_transform.basis.x
	var up: Vector3 = global_transform.basis.y
	
	# Calculate distance to avoid speed inconsistencies across zoom levels
	var radius: float = global_position.distance_to(orbit_target)
	var dynamic_speed: float = max(radius, 0.5) * pan_speed * base_pan_speed
	
	global_position += right * -relative_mouse.x * dynamic_speed
	global_position += up * relative_mouse.y * dynamic_speed

## Moves the camera closer to or further from the target proportionally
func zoom(direction_amount: float) -> void:
	var radius: float = global_position.distance_to(orbit_target)
	
	var forward: Vector3 = global_transform.basis.z
	var zoom_step: float = radius * base_zoom_step * direction_amount
	var new_position: Vector3 = global_position + forward * zoom_step * zoom_speed
	
	radius = new_position.distance_to(orbit_target)
	if radius < minimum_orbit_radius:
		return
	
	global_position = new_position

## Rotates the camera in place (FPS/Free-look style)
func rotate_free(relative_mouse: Vector2) -> void:
	yaw -= relative_mouse.x * orbit_speed * base_orbit_speed
	pitch -= relative_mouse.y * orbit_speed * base_orbit_speed
	pitch = clamp(pitch, deg_to_rad(-89), deg_to_rad(89))
	
	rotation = Vector3(pitch, yaw, 0)

## Orbits the camera around a specific 3D coordinate point in space
func orbit(relative_mouse: Vector2, target_point: Vector3) -> void:
	yaw -= relative_mouse.x * orbit_speed * base_orbit_speed
	pitch -= relative_mouse.y * orbit_speed * base_orbit_speed
	pitch = clamp(pitch, deg_to_rad(-89), deg_to_rad(89))
	
	var radius: float = global_position.distance_to(target_point)
	
	var target_basis: Basis = Basis.from_euler(Vector3(pitch, yaw, 0))
	global_transform.basis = target_basis
	global_position = target_point + target_basis.z * radius
