@tool
class_name BoxGizmo extends SelectionGizmo

const PointGizmoScn: PackedScene = preload("res://scenes/gizmos/PointGizmo.tscn")

var _points: Array[PointGizmo] = []


func get_aabb() -> AABB:
	var min_bound: Vector3 = Vector3.INF
	var max_bound: Vector3 = -Vector3.INF
	
	for point in _points:
		min_bound = min_bound.min(point.position)
		max_bound = max_bound.max(point.position)
	
	return AABB(min_bound, max_bound - min_bound)


func set_aabb(aabb: AABB) -> void:
	_fit_points_to_aabb(aabb)


func _ready() -> void:
	for i in 8:
		var gizmo: PointGizmo = PointGizmoScn.instantiate()
		_points.append(gizmo)
		add_child(gizmo)
	
	_fit_points_to_aabb(AABB(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 1.0, 1.0)))


func _fit_points_to_aabb(aabb: AABB) -> void:
	
	var coords: Array[Vector3] = [
		aabb.position + Vector3(0.0, 0.0, 0.0) * aabb.size,
		aabb.position + Vector3(1.0, 0.0, 0.0) * aabb.size,
		aabb.position + Vector3(0.0, 0.0, 1.0) * aabb.size,
		aabb.position + Vector3(1.0, 0.0, 1.0) * aabb.size,
		aabb.position + Vector3(0.0, 1.0, 0.0) * aabb.size,
		aabb.position + Vector3(1.0, 1.0, 0.0) * aabb.size,
		aabb.position + Vector3(0.0, 1.0, 1.0) * aabb.size,
		aabb.position + Vector3(1.0, 1.0, 1.0) * aabb.size,
	]
	
	# update corner handles
	
	for i in coords.size():
		_points[i].position = coords[i]
	
	# update edges
	
	var mesh: ImmediateMesh = %EdgeMesh.mesh as ImmediateMesh
	mesh.clear_surfaces()
	
	mesh.surface_begin(Mesh.PRIMITIVE_LINES)
	
	var from: Array[Vector3] = [
		coords[0], coords[0], coords[3], coords[3],
		coords[4], coords[4], coords[7], coords[7],
		coords[0], coords[1], coords[2], coords[3],
	]
	
	var to: Array[Vector3] = [
		coords[1], coords[2], coords[1], coords[2],
		coords[5], coords[6], coords[5], coords[6],
		coords[4], coords[5], coords[6], coords[7],
	]
	
	for i in 12:
		mesh.surface_add_vertex(from[i])
		mesh.surface_add_vertex(to[i])
	
	mesh.surface_end()


func _fit_aabb_to_point(point: PointGizmo) -> AABB:
	var opposite: PointGizmo = point
	var max_distance: float = 0.0
	
	for p in _points:
		var distance: float = point.position.distance_to(p.position)
		if distance > max_distance:
			opposite = p
			max_distance = distance
	
	var min_bound: Vector3 = point.position.min(opposite.position)
	var max_bound: Vector3 = point.position.max(opposite.position)
	
	return AABB(min_bound, max_bound - min_bound)


func _edit_begin(mpos: Vector2, camera: Camera3D) -> bool:
	_is_editing = _points.any(
		func (point: PointGizmo) -> bool:
			point.edit_begin(mpos, camera)
			return point.is_editing()
	)
	
	return _is_editing


func _edit(mpos: Vector2, camera: Camera3D) -> void:
	var i: int = _points.find_custom(
		func (point: PointGizmo) -> bool:
			return point.is_editing()
	)
	
	_points[i].edit(mpos, camera)
	_fit_points_to_aabb(_fit_aabb_to_point(_points[i]))


func _edit_end(mpos: Vector2, camera: Camera3D) -> void:
	var i: int = _points.find_custom(
		func (point: PointGizmo) -> bool:
			return point.is_editing()
	)
	
	_points[i].edit_end(mpos, camera)
	_fit_points_to_aabb(_fit_aabb_to_point(_points[i]))
	_is_editing = false
