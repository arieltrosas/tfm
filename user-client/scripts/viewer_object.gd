class_name ViewerObject extends Node3D

const BASE_POINT_SIZE: float = 1e-3

enum ViewMode { POINT_CLOUD, MESH }
const POINT_CLOUD = ViewMode.POINT_CLOUD
const MESH = ViewMode.MESH

@export var view_mode: ViewMode = POINT_CLOUD: set = _set_view_mode
@export_global_file var source_path: String = ""

var _mtime_seconds: int = 0


func update_object() -> void:
	if not FileAccess.file_exists(source_path):
		return
	
	var mtime: int = FileAccess.get_modified_time(source_path)
	if mtime != _mtime_seconds:
		_mtime_seconds = mtime
		_load_object()


func set_point_size(size: float) -> void:
	var mesh: QuadMesh = %PointCloudView.multimesh.mesh as QuadMesh
	mesh.size = Vector2.ONE * BASE_POINT_SIZE * clamp(size, 1e-3, 1.0)


func _set_view_mode(value: ViewMode) -> void:
	view_mode = value
	%PointCloudView.visible = false
	%MeshView.visible = false
	
	match view_mode:
		POINT_CLOUD: %PointCloudView.visible = true
		MESH: %MeshView.visible = true


func _load_object() -> void:
	var file = FileAccess.open(source_path, FileAccess.READ)
	if not file or not file.is_open():
		return
	
	var ply := PLY.new()
	ply.parse(file)
	
	var fatal: bool = false
	for i in ply.get_error_count():
		fatal = ply.get_error(i) in [PLY.NOT_PLY, PLY.BAD_FORMAT]
		printerr("PLY: Error parsing file '%s': %s" % [source_path, ply.get_error_msg(i)])
	
	if fatal:
		return
	
	# load the point cloud view
	
	var mmesh: MultiMesh = %PointCloudView.multimesh
	
	mmesh.instance_count = ply.get_vertex_count()
	for i in mmesh.instance_count:
		mmesh.set_instance_transform(i, Transform3D.IDENTITY.translated(ply.get_vertex_position(i)))
		mmesh.set_instance_color(i, ply.get_vertex_color(i))
	
	# load the mesh view
	
	var mesh: ArrayMesh = %MeshView.mesh as ArrayMesh
	mesh.clear_surfaces()
	
	if not ply.get_face_count():
		return
	
	var vertex_arr: PackedVector3Array = []
	var color_arr: PackedColorArray = []
	var index_arr: PackedInt32Array = []
	
	vertex_arr.resize(ply.get_vertex_count())
	color_arr.resize(ply.get_vertex_count())
	
	for i in ply.get_vertex_count():
		vertex_arr[i] = ply.get_vertex_position(i)
		color_arr[i] = ply.get_vertex_color(i)
	
	for i in ply.get_face_count():
		var face = ply.get_face_indices(i)
		face.reverse()
		for index in face:
			index_arr.push_back(index)
	
	var surface_array = []
	surface_array.resize(ArrayMesh.ARRAY_MAX)
	surface_array[ArrayMesh.ARRAY_VERTEX] = vertex_arr
	surface_array[ArrayMesh.ARRAY_COLOR] = color_arr
	surface_array[ArrayMesh.ARRAY_INDEX] = index_arr
	
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, surface_array)
