class_name WorkspaceItem extends PanelContainer

@export var SelectedStyleBox: StyleBox

signal visibility_toggled(visible: bool)

var file_name: String = "": set = _set_file_name
var selected: bool = false: set = _set_selected


func enable_toggles(enabled: bool) -> void:
	%VisibleToggle.visible = enabled


func _set_file_name(value: String) -> void:
	file_name = value
	%Label.text = file_name


func _set_selected(value: bool) -> void:
	selected = value
	if selected:
		add_theme_stylebox_override("panel", SelectedStyleBox)
	else:
		remove_theme_stylebox_override("panel")


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var e := event as InputEventMouseButton
		if e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
			selected = not selected


func _on_visible_toggle_toggled(toggled_on: bool) -> void:
	visibility_toggled.emit(not toggled_on)
