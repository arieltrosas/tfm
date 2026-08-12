class_name MeshIntersect extends Object

const EPSILON := 0.000001

# Returns the distance along the ray to the intersection,
# or INF if there is no intersection.
static func ray_intersect_triangle(
	origin: Vector3,
	direction: Vector3,
	a: Vector3,
	b: Vector3,
	c: Vector3
) -> float:
	var edge1 := b - a
	var edge2 := c - a
	
	var h := direction.cross(edge2)
	var det := edge1.dot(h)
	
	# Ray is parallel to the triangle.
	if abs(det) < EPSILON:
		return INF
	
	var inv_det := 1.0 / det
	
	var s := origin - a
	var u := s.dot(h) * inv_det
	
	if u < 0.0 or u > 1.0:
		return INF
	
	var q := s.cross(edge1)
	var v := direction.dot(q) * inv_det
	
	if v < 0.0 or u + v > 1.0:
		return INF
	
	var t := edge2.dot(q) * inv_det
	
	if t < 0.0:
		return INF
	
	return t


# Returns the closest world-space intersection point,
# or null if the ray doesn't hit the mesh.
static func ray_intersect_mesh(
	mesh: Mesh,
	mesh_transform: Transform3D,
	ray_origin: Vector3,
	ray_direction: Vector3
) -> Variant:
	
	var inverse_transform := mesh_transform.affine_inverse()
	
	var local_origin := inverse_transform * ray_origin
	var local_direction := inverse_transform.basis * ray_direction
	
	var closest_t := INF
	
	for surface_index in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(surface_index)
	
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	
		if indices.is_empty():
			for i in range(0, vertices.size(), 3):
				var t := ray_intersect_triangle(
					local_origin,
					local_direction,
					vertices[i],
					vertices[i + 1],
					vertices[i + 2]
				)
				
				if t < closest_t:
					closest_t = t
		else:
			for i in range(0, indices.size(), 3):
				var t := ray_intersect_triangle(
					local_origin,
					local_direction,
					vertices[indices[i]],
					vertices[indices[i + 1]],
					vertices[indices[i + 2]]
				)
				
				if t < closest_t:
					closest_t = t
	
	if closest_t == INF:
		return null
	
	var local_hit: Vector3 = local_origin + local_direction * closest_t
	return mesh_transform * local_hit


static func ray_intersect_scene(
	root: Node3D,
	ray_origin: Vector3,
	ray_direction: Vector3
) -> Variant:
	var closest_point: Variant = null
	var closest_distance_squared := INF

	var mesh_nodes: Array[Node] = root.find_children("*", "MeshInstance3D")
	if root is MeshInstance3D:
		mesh_nodes.append(root)

	for mesh_node in mesh_nodes:
		var mesh_instance := mesh_node as MeshInstance3D

		if mesh_instance.mesh == null:
			continue

		var hit: Variant = ray_intersect_mesh(
			mesh_instance.mesh,
			mesh_instance.global_transform,
			ray_origin,
			ray_direction
		)

		if hit == null:
			continue

		var distance_squared: float = ray_origin.distance_squared_to(hit)

		if distance_squared < closest_distance_squared:
			closest_distance_squared = distance_squared
			closest_point = hit

	return closest_point
