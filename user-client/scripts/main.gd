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
	var host_edit = %AuthPopup.get_node("MarginContainer/VBoxContainer/VBoxContainer/HostInput") as LineEdit
	var key_edit = %AuthPopup.get_node("MarginContainer/VBoxContainer/VBoxContainer/KeyInput") as LineEdit
	
	var host = host_edit.text
	var key = key_edit.text
	
	key_edit.text = ""
	
	var info = ""
	
	if not host:
		var success = await BackendAPI.connect_ollama("", "")
		if success:
			info = "Successfully connected to local Ollama instance."
		else:
			info = "Failed to connect to local Ollama instance."
	else:
		var success = await BackendAPI.connect_openai(host, key)
		
		if success:
			info = "Successfully connected to OpenAI-compatible host."
		else:
			var fallback_success = await BackendAPI.connect_ollama("", "")
			if fallback_success:
				info = "Failed to connect to OpenAI host. Fell back to local Ollama instance."
			else:
				info = "Failed to connect to OpenAI host, and local Ollama fallback failed."
	
	%InfoPopup.get_node("MarginContainer/VBoxContainer/Label").text = info
	
	%AuthPopup.hide()
	%InfoPopup.popup_centered()


func _on_cancel_pressed() -> void:
	%AuthPopup.hide()
