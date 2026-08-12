@tool
class_name PointGizmo extends SelectionGizmo

func get_point() -> Vector3:
	return self.global_position


func set_point(point: Vector3) -> void:
	self.global_position = point


func _edit_begin(mpos: Vector2, camera: Camera3D) -> bool:
	var sphere_mesh: SphereMesh = %PointMesh.mesh as SphereMesh
	var pick_radius_pixels: float = sphere_mesh.radius * %PointMesh.scale.x * get_viewport().get_visible_rect().size.x
	var screen_pos: Vector2 = camera.unproject_position(self.global_position)
	var dist: float = mpos.distance_to(screen_pos)
	return dist <= pick_radius_pixels


func _edit(mpos: Vector2, camera: Camera3D) -> void:
	var ray_origin: Vector3 = camera.project_ray_origin(mpos)
	var ray_dir: Vector3 = camera.project_ray_normal(mpos)

	var plane := Plane(
		camera.global_transform.basis.z,
		self.global_position
	)

	var hit = plane.intersects_ray(ray_origin, ray_dir)
	if hit == null:
		return

	self.global_position = hit
