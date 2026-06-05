extends MarginContainer


func _on_workspace_viewer_object_added(object: ViewerObject) -> void:
	%Viewer.add_object(object)


func _on_workspace_viewer_object_removed(object: ViewerObject) -> void:
	%Viewer.remove_object(object)
