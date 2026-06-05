class_name ChatUserMsg extends HBoxContainer

func set_msg(msg: String) -> void:
	%Msg.text = msg


func get_msg() -> String:
	return %Msg.text
