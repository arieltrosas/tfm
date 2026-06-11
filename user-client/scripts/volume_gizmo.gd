@tool
class_name VolumeGizmo extends MeshInstance3D

# Signals

signal volume_changed(volume: AABB)


# Disable Gizmo

@export var disabled: bool = false

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
# INTERNAL DRAG STATE (ADDED)
# ------------------------------------------------------------

var _corner_handles: Array[Area3D] = []
var _dragging_corner: int = -1


# ------------------------------------------------------------
# INTERNAL
# ------------------------------------------------------------

func _ready() -> void:
	_ensure_materials()
	_apply_materials()
	_rebuild()

	if _corner_handles.is_empty():
		_create_corner_handles()


# ------------------------------------------------------------
# MATERIAL FUNCTIONS (UNCHANGED)
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
		mesh.surface_set_material(0, edge_material)

	if mesh.get_surface_count() > 1 and corner_material:
		mesh.surface_set_material(1, corner_material)

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
	_add_corner_mesh(result)

	mesh = result
	_apply_materials()

	if _corner_handles.is_empty():
		_create_corner_handles()

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
# CORNER HANDLES (ADDED)
# ------------------------------------------------------------

func _create_corner_handles() -> void:
	for h in _corner_handles:
		if is_instance_valid(h):
			h.queue_free()

	_corner_handles.clear()

	for i in range(8):
		var area := Area3D.new()
		area.name = "CornerHandle_%d" % i

		var shape := BoxShape3D.new()
		shape.size = Vector3.ONE * corner_radius * 2.0

		var col := CollisionShape3D.new()
		col.shape = shape
		area.add_child(col)

		add_child(area)

		area.input_ray_pickable = true
		area.collision_layer = 1
		area.collision_mask = 1

		_corner_handles.append(area)


func _update_corner_handles() -> void:
	var corners := get_corners()
	
	for i in _corner_handles.size():
		var handle: Node3D = _corner_handles[i]
		if is_instance_valid(_corner_handles[i]) and handle.is_inside_tree():
			_corner_handles[i].global_position = global_transform * corners[i]


# ------------------------------------------------------------
# DRAG API (ADDED - external input driven)
# ------------------------------------------------------------

func is_dragging() -> bool:
	return _dragging_corner != -1 or disabled


func try_start_drag(mouse_pos: Vector2, cam: Camera3D) -> void:
	if disabled: return
	
	var from := cam.project_ray_origin(mouse_pos)
	var to := from + cam.project_ray_normal(mouse_pos) * 1000.0

	var space := get_world_3d().direct_space_state
	var query := PhysicsRayQueryParameters3D.create(from, to)
	query.collide_with_areas = true

	var hit := space.intersect_ray(query)
	if hit.is_empty():
		return

	var collider = hit["collider"]

	for i in range(_corner_handles.size()):
		if collider == _corner_handles[i]:
			_dragging_corner = i
			return


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
		0:
			min_v = p
	
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
		6:
			max_v = p
		7:
			min_v.x = p.x
			max_v.y = p.y
			max_v.z = p.z
	
	box = AABB(
		min_v.min(max_v),
		(min_v - max_v).abs()
	)
	
	_rebuild()


# ------------------------------------------------------------
# CORNER MESH (UNCHANGED)
# ------------------------------------------------------------

func _add_corner_mesh(result: ArrayMesh) -> void:
	var sphere := SphereMesh.new()
	sphere.radius = corner_radius
	sphere.height = corner_radius * 2.0
	sphere.radial_segments = corner_segments
	sphere.rings = corner_segments

	var arrays := sphere.get_mesh_arrays()

	var src_vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var src_normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var src_indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]

	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var indices := PackedInt32Array()

	var corners := get_corners()
	var vertex_offset := 0

	for corner in corners:
		for v in src_vertices:
			vertices.push_back(v + corner)
			colors.push_back(corner_color)

		for n in src_normals:
			normals.push_back(n)

		for idx in src_indices:
			indices.push_back(idx + vertex_offset)

		vertex_offset += src_vertices.size()

	var mesh_arrays := []
	mesh_arrays.resize(Mesh.ARRAY_MAX)

	mesh_arrays[Mesh.ARRAY_VERTEX] = vertices
	mesh_arrays[Mesh.ARRAY_NORMAL] = normals
	mesh_arrays[Mesh.ARRAY_COLOR] = colors
	mesh_arrays[Mesh.ARRAY_INDEX] = indices

	result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh_arrays)


# ------------------------------------------------------------
# EDGE MESH (UNCHANGED)
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
