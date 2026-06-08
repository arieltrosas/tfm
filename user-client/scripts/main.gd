extends MarginContainer


func _on_workspace_viewer_object_added(object: ViewerObject) -> void:
	%Viewer.add_object(object)


func _on_workspace_viewer_object_removed(object: ViewerObject) -> void:
	%Viewer.remove_object(object)


func _on_auth_button_pressed() -> void:
	%AuthPopup.popup_centered()


func _on_info_popup_ok_pressed() -> void:
	%InfoPopup.hide()


func _on_auth_popup_accept_pressed() -> void:
	var host = (%AuthPopup.get_node("MarginContainer/VBoxContainer/VBoxContainer/HostInput") as LineEdit).text
	var key = (%AuthPopup.get_node("MarginContainer/VBoxContainer/VBoxContainer/KeyInput") as LineEdit).text
	
	var info
	if await BackendAPI.auth(host, key):
		info = "Succesfully connected to: %s" % host
	else:
		info = "Error connecting to: %s" % host
	
	%InfoPopup.get_node("MarginContainer/VBoxContainer/Label").text = info
	
	%AuthPopup.hide()
	%InfoPopup.popup_centered()


func _on_cancel_pressed() -> void:
	%AuthPopup.hide()
