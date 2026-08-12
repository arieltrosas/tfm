class_name SelectionsListItem extends PanelContainer

@export var SelectedStyleBox: StyleBox

var id: String = "": set = _set_id
var selected: bool = false: set = _set_selected


func _set_id(value: String) -> void:
	id = value
	%Label.text = id


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
