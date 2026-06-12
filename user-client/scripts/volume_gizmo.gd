@tool
class_name VolumeGizmo extends MeshInstance3D

# Signals
signal volume_changed(volume: AABB)

# Disable Gizmo
@export var disabled: bool = false


# Selection Pixel Radius (in Screen space)
@export var selection_radius_px: float = 24.0


# Volume
@export var box: AABB = AABB(Vector3.ZERO, Vector3.ONE):
	set(value):
		box = value
		_rebuild()

# Colors
@export var edge_color: Color = Color.CYAN:
	set(value):
		edge_color = value
		_apply_colors()

@export var corner_color: Color = Color.CORAL:
	set(value):
		corner_color = value
		_apply_colors()

# Materials
@export var edge_material: StandardMaterial3D:
	set(value):
		edge_material = value
		_apply_materials()

@export var corner_material: StandardMaterial3D:
	set(value):
		corner_material = value
		_apply_materials()

# Geometry
@export_range(0.001, 0.5, 0.001)
var edge_thickness: float = 0.01:
	set(value):
		edge_thickness = value
		_rebuild()

@export_range(0.001, 10.0, 0.001)
var corner_radius: float = 0.1:
	set(value):
		corner_radius = value
		_rebuild()

@export_range(1, 32, 1)
var corner_segments: int = 8:
	set(value):
		corner_segments = value
		_rebuild()


# ------------------------------------------------------------
# INTERNAL DRAG STATE
# ------------------------------------------------------------

var _corner_handles: Array[MeshInstance3D] = []
var _dragging_corner: int = -1


# ------------------------------------------------------------
# INTERNAL
# ------------------------------------------------------------

func _ready() -> void:
	_ensure_materials()
	_apply_materials()
	_rebuild()


# ------------------------------------------------------------
# MATERIAL FUNCTIONS
# ------------------------------------------------------------

func _ensure_materials() -> void:
	if edge_material == null:
		edge_material = StandardMaterial3D.new()
		edge_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		edge_material.vertex_color_use_as_albedo = true
		edge_material.no_depth_test = true
		edge_material.render_priority = 1

	if corner_material == null:
		corner_material = StandardMaterial3D.new()
		corner_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		corner_material.vertex_color_use_as_albedo = true
		corner_material.no_depth_test = true
		corner_material.render_priority = 2


func _apply_materials() -> void:
	if mesh == null:
		return

	if mesh.get_surface_count() > 0 and edge_material:
		set_surface_override_material(0, edge_material)

	# Update materials on individual corner meshes
	for mesh_instance in _corner_handles:
		if is_instance_valid(mesh_instance):
			mesh_instance.material_override = corner_material

	_apply_colors()


func _apply_colors() -> void:
	if edge_material:
		edge_material.albedo_color = edge_color

	if corner_material:
		corner_material.albedo_color = corner_color


# ------------------------------------------------------------
# BUILD
# ------------------------------------------------------------

func _rebuild() -> void:
	var result := ArrayMesh.new()
	_add_edge_mesh(result)
	mesh = result

	if _corner_handles.is_empty():
		_create_corner_handles()
	else:
		_update_corner_meshes()

	_update_corner_handles()


# ------------------------------------------------------------
# CORNERS
# ------------------------------------------------------------

func get_corners() -> Array[Vector3]:
	var p0 := box.position
	var p1 := box.position + box.size

	return [
		Vector3(p0.x, p0.y, p0.z),
		Vector3(p1.x, p0.y, p0.z),
		Vector3(p1.x, p1.y, p0.z),
		Vector3(p0.x, p1.y, p0.z),

		Vector3(p0.x, p0.y, p1.z),
		Vector3(p1.x, p0.y, p1.z),
		Vector3(p1.x, p1.y, p1.z),
		Vector3(p0.x, p1.y, p1.z),
	]


# ------------------------------------------------------------
# CORNER HANDLES (VISUAL ONLY)
# ------------------------------------------------------------

func _clear_old_handles() -> void:
	_corner_handles.clear()
	var targets: Array[Node] = []
	for child in get_children():
		if child.name.begins_with("CornerMesh_"):
			targets.append(child)
	for child in targets:
		remove_child(child)
		child.free()


func _create_corner_handles() -> void:
	_clear_old_handles()
	var sphere_mesh := _generate_sphere_mesh()

	for i in range(8):
		var mesh_instance := MeshInstance3D.new()
		mesh_instance.name = "CornerMesh_%d" % i
		mesh_instance.mesh = sphere_mesh
		if corner_material:
			mesh_instance.material_override = corner_material

		add_child(mesh_instance)
		_corner_handles.append(mesh_instance)


func _update_corner_meshes() -> void:
	var sphere_mesh := _generate_sphere_mesh()
	for mesh_instance in _corner_handles:
		if is_instance_valid(mesh_instance):
			mesh_instance.mesh = sphere_mesh


func _generate_sphere_mesh() -> SphereMesh:
	var sphere := SphereMesh.new()
	sphere.radius = corner_radius
	sphere.height = corner_radius * 2.0
	sphere.radial_segments = corner_segments
	sphere.rings = corner_segments
	return sphere


func _update_corner_handles() -> void:
	var corners := get_corners()
	for i in _corner_handles.size():
		var mesh_instance := _corner_handles[i]
		if is_instance_valid(mesh_instance) and mesh_instance.is_inside_tree():
			mesh_instance.position = corners[i]


# ------------------------------------------------------------
# DRAG API (2D SCREEN SPACE SELECTION)
# ------------------------------------------------------------

func is_dragging() -> bool:
	return _dragging_corner != -1 or disabled


func try_start_drag(mouse_pos: Vector2, cam: Camera3D) -> void:
	if disabled: return
	
	var closest_index := -1
	
	var click_radius_pixels := selection_radius_px
	var min_distance := click_radius_pixels
	
	for i in range(_corner_handles.size()):
		var handle := _corner_handles[i]
		if not is_instance_valid(handle) or not handle.is_inside_tree():
			continue
			
		# Skip handles that are physically located behind the camera view plane
		if cam.is_position_behind(handle.global_position):
			continue
			
		# Unproject the handle's 3D position to 2D screen coordinates
		var screen_pos := cam.unproject_position(handle.global_position)
		var distance_to_mouse := mouse_pos.distance_to(screen_pos)
		
		if distance_to_mouse < min_distance:
			min_distance = distance_to_mouse
			closest_index = i
			
	if closest_index != -1:
		_dragging_corner = closest_index


func update_drag(mouse_pos: Vector2, cam: Camera3D) -> void:
	if _dragging_corner == -1 or disabled:
		return

	var ray_origin := cam.project_ray_origin(mouse_pos)
	var ray_dir := cam.project_ray_normal(mouse_pos)

	var plane := Plane(
		cam.global_transform.basis.z,
		_corner_handles[_dragging_corner].global_position
	)

	var hit = plane.intersects_ray(ray_origin, ray_dir)
	if hit == null:
		return

	var local := to_local(hit)
	_set_corner(_dragging_corner, local)


func end_drag() -> void:
	_dragging_corner = -1
	volume_changed.emit(box)


func _set_corner(i: int, p: Vector3) -> void:
	var min_v := box.position
	var max_v := box.position + box.size
	
	match i:
		0: min_v = p
		1:
			min_v.y = p.y
			min_v.z = p.z
			max_v.x = p.x
		2:
			min_v.z = p.z
			max_v.x = p.x
			max_v.y = p.y
		3:
			min_v.x = p.x
			min_v.z = p.z
			max_v.y = p.y
		4:
			min_v.x = p.x
			min_v.y = p.y
			max_v.z = p.z
		5:
			min_v.y = p.y
			max_v.x = p.x
			max_v.z = p.z
		6: max_v = p
		7:
			min_v.x = p.x
			max_v.y = p.y
			max_v.z = p.z
	
	var real_min := min_v.min(max_v)
	var real_max := min_v.max(max_v)
	
	box = AABB(real_min, real_max - real_min)


# ------------------------------------------------------------
# EDGE MESH
# ------------------------------------------------------------

func _add_edge_mesh(result: ArrayMesh) -> void:
	var corners := get_corners()

	var edges := [
		[0, 1], [1, 2], [2, 3], [3, 0],
		[4, 5], [5, 6], [6, 7], [7, 4],
		[0, 4], [1, 5], [2, 6], [3, 7],
	]

	var vertices := PackedVector3Array()
	var colors := PackedColorArray()

	for e in edges:
		vertices.push_back(corners[e[0]])
		vertices.push_back(corners[e[1]])

		colors.push_back(edge_color)
		colors.push_back(edge_color)

	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)

	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_COLOR] = colors

	result.add_surface_from_arrays(Mesh.PRIMITIVE_LINES, arrays)
