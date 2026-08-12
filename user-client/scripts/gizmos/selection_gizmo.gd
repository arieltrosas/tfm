class_name SelectionGizmo extends Node3D

signal gizmo_edited

var _is_editing: bool = false


func is_editing() -> bool:
	return _is_editing


func edit_begin(mpos: Vector2, camera: Camera3D) -> void:
	if _is_editing:
		return
	_is_editing = _edit_begin(mpos, camera)


func edit(mpos: Vector2, camera: Camera3D) -> void:
	if not _is_editing:
		return
	_edit(mpos, camera)


func edit_end(mpos: Vector2, camera: Camera3D) -> void:
	if not _is_editing:
		return
	_edit_end(mpos, camera)
	_is_editing = false
	gizmo_edited.emit()


func _edit_begin(_mpos: Vector2, _camera: Camera3D) -> bool:
	return false


func _edit(_mpos: Vector2, _camera: Camera3D) -> void:
	pass


func _edit_end(_mpos: Vector2, _camera: Camera3D) -> void:
	pass
