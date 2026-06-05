class_name ChatEngineMsg extends VBoxContainer


func set_msg(msg: String) -> void:
	%Msg.text = msg


func get_msg() -> String:
	return %Msg.text
