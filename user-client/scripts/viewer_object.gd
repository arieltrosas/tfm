class_name ViewerObject extends Node3D

const BASE_POINT_SIZE: float = 1e-3

enum ViewMode { POINT_CLOUD, MESH }
const POINT_CLOUD = ViewMode.POINT_CLOUD
const MESH = ViewMode.MESH

@export_global_file var source_path: String = ""
var view_mode: ViewMode = MESH: set = _set_view_mode

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
		printerr("PLY: Failed to open file '%s'" % source_path)
		return
	
	var ply := PLY.new()
	ply.parse(file)
	
	var fatal: bool = false
	for i in ply.get_error_count():
		fatal = fatal or (ply.get_error(i) in [PLY.NOT_PLY, PLY.BAD_FORMAT])
		printerr("PLY: Error parsing file '%s': %s" % [source_path, ply.get_error_msg(i)])
	
	if fatal:
		return
		
	var vcount := ply.get_vertex_count()
	if vcount == 0:
		return
	
	# --- 1. Load the Point Cloud View ---
	
	var mmesh: MultiMesh = %PointCloudView.multimesh
	if mmesh:
		mmesh.instance_count = vcount
		for i in vcount:
			# Cache the position to minimize cross-language overhead
			var pos := ply.get_vertex_position(i) 
			mmesh.set_instance_transform(i, Transform3D(Basis(), pos))
			mmesh.set_instance_color(i, ply.get_vertex_color(i))
	
	# --- 2. Load the Mesh View ---
	
	if not %MeshView:
		return
		
	var mesh: ArrayMesh = %MeshView.mesh as ArrayMesh
	if not mesh:
		mesh = ArrayMesh.new()
		%MeshView.mesh = mesh
	else:
		mesh.clear_surfaces()
	
	var fcount := ply.get_face_count()
	if not fcount:
		return
	
	var vertex_arr := PackedVector3Array()
	var color_arr := PackedColorArray()
	var normal_arr := PackedVector3Array()
	var index_arr := PackedInt32Array()
	
	vertex_arr.resize(vcount)
	color_arr.resize(vcount)
	normal_arr.resize(vcount)
	
	for i in vcount:
		vertex_arr[i] = ply.get_vertex_position(i)
		color_arr[i] = ply.get_vertex_color(i)
		normal_arr[i] = ply.get_vertex_normal(i)
	
	for i in fcount:
		var face := ply.get_face_indices(i)
		if face.size() < 3:
			continue
		
		face.reverse()
		
		for j in range(1, face.size() - 1):
			index_arr.push_back(face[0])
			index_arr.push_back(face[j])
			index_arr.push_back(face[j + 1])
	
	var surface_array := []
	surface_array.resize(Mesh.ARRAY_MAX)
	surface_array[Mesh.ARRAY_VERTEX] = vertex_arr
	surface_array[Mesh.ARRAY_COLOR] = color_arr
	surface_array[Mesh.ARRAY_INDEX] = index_arr
	surface_array[Mesh.ARRAY_NORMAL] = normal_arr
	
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, surface_array)
