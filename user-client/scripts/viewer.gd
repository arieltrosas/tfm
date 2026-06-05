class_name Viewer extends PanelContainer

@export var point_size: float:
	set = set_point_size

var viewer_objects: Array[ViewerObject]


func add_object(object: ViewerObject) -> void:
	if object in viewer_objects:
		return
	viewer_objects.append(object)
	%Viewer3D.add_child(object)
	_update_objects()


func remove_object(object: ViewerObject) -> void:
	if object not in viewer_objects:
		return
	viewer_objects.erase(object)
	%Viewer3D.remove_child(object)


func set_point_size(value: float) -> void:
	point_size = value
	_update_objects()


func _on_point_size_slider_value_changed(value: float) -> void:
	point_size = value


func _update_objects() -> void:
	for object in viewer_objects:
		object.set_point_size(point_size)
		object.update_object()


func _on_object_update_timer_timeout() -> void:
	_update_objects()
