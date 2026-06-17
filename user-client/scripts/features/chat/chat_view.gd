class_name ChatView extends PanelContainer

const ChatUserMsgScn = preload("res://scenes/ui/ChatUserMsg.tscn")
const ChatEngineMsgScn = preload("res://scenes/ui/ChatEngineMsg.tscn")

var _service: ChatService
var server_thinking: bool = false


func setup(service: ChatService) -> void:
	_service = service
	AppEventBus.chat_response_received.connect(_on_chat_response_received)
	AppEventBus.models_changed.connect(_on_models_changed)


func _ready() -> void:
	pass


func send_message() -> void:
	if not %ChatBox.text or server_thinking:
		return

	var msg_text: String = %ChatBox.text
	%ChatBox.clear()

	var user_msg: ChatUserMsg = ChatUserMsgScn.instantiate()
	user_msg.set_msg(msg_text)
	_display_message(user_msg)

	server_thinking = true
	await _service.send_message(msg_text)
	server_thinking = false


func _on_chat_response_received(response: String) -> void:
	var engine_msg: ChatEngineMsg = ChatEngineMsgScn.instantiate()
	engine_msg.set_msg(response)
	_display_message(engine_msg)


func _on_send_button_pressed() -> void:
	send_message()


func _display_message(msg: Control) -> void:
	%MsgList.add_child(msg)
	await get_tree().process_frame
	var sb: VScrollBar = %MsgListScroll.get_v_scroll_bar()
	sb.value = sb.max_value


func _on_chat_box_gui_input(event: InputEvent) -> void:
	if event is InputEventKey:
		var e := event as InputEventKey
		if e.keycode == KEY_ENTER and not e.is_echo() and e.pressed and not e.shift_pressed:
			%ChatBox.accept_event()
			send_message()
		elif e.keycode == KEY_ENTER and not e.is_echo() and e.pressed and e.shift_pressed:
			%ChatBox.insert_text_at_caret("\n")


func _on_models_changed(models: Array[String]) -> void:
	%ModelButton.clear()
	for model in models:
		%ModelButton.add_item(model)
	_sync_model_selection()


func _sync_model_selection() -> void:
	var current := await _service.get_current_model_name()
	%ModelButton.selected = _service.available_models.find(current)


func _on_model_button_item_selected(index: int) -> void:
	if not await _service.set_model(%ModelButton.get_item_text(index)):
		%ModelButton.selected = -1


func _on_model_upate_timer_timeout() -> void:
	await _service.refresh_models()
	_sync_model_selection()
