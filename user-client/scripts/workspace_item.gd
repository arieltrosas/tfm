class_name WorkspaceItem extends PanelContainer

@export var SelectedStyleBox: StyleBox

signal mesh_button_toggled(toggled_on: bool)
signal cloud_button_toggled(toggled_on: bool)
signal visible_button_toggled(toggled_on: bool)


var file_name: String = "": set = _set_file_name
var selected: bool = false: set = _set_selected


func set_view_mode_toggles_visible(enabled: bool) -> void:
	%MeshButton.visible = enabled
	%CloudButton.visible = enabled
	%VisibleButton.visible = enabled


func _ready() -> void:
	var view_mode_button_group := ButtonGroup.new()
	%MeshButton.button_group = view_mode_button_group
	%CloudButton.button_group = view_mode_button_group


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


func _on_mesh_button_toggled(toggled_on: bool) -> void:
	mesh_button_toggled.emit(toggled_on)


func _on_cloud_button_toggled(toggled_on: bool) -> void:
	cloud_button_toggled.emit(toggled_on)


func _on_visible_button_toggled(toggled_on: bool) -> void:
	visible_button_toggled.emit(toggled_on)
