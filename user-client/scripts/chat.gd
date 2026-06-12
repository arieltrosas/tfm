class_name Chat extends PanelContainer

const ChatUserMsgScn = preload("res://scenes/ui/ChatUserMsg.tscn")
const ChatEngineMsgScn = preload("res://scenes/ui/ChatEngineMsg.tscn")

var server_thinking: bool = false
var available_models: Array[String] = []


func _ready() -> void:
	BackendAPI.backend_ready.connect(_update_models_button, CONNECT_ONE_SHOT)
	_update_models_button()


func send_message() -> void:
	if not %ChatBox.text or server_thinking:
		return
	
	var msg_text: String = %ChatBox.text
	%ChatBox.clear()
	
	var user_msg: ChatUserMsg = ChatUserMsgScn.instantiate()
	user_msg.set_msg(msg_text)
	_display_message(user_msg)
	
	server_thinking = true
	var response_msg = await BackendAPI.chat(msg_text)
	server_thinking = false
	
	var engine_msg: ChatEngineMsg = ChatEngineMsgScn.instantiate()
	engine_msg.set_msg(response_msg)
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
		var is_enter: bool = e.keycode == KEY_ENTER
		var is_echo: bool = e.is_echo()
		var is_shift: bool = e.shift_pressed
		var is_pressed: bool = e.pressed
		
		if is_enter and not is_echo and is_pressed and not is_shift:
			%ChatBox.accept_event()
			send_message()
		elif is_enter and not is_echo and is_pressed and is_shift:
			%ChatBox.insert_text_at_caret("\n")


func _update_models_button() -> void:
	# 1. Fetch the latest models from the API
	var new_models: Array[String] = []
	for m in await BackendAPI.model_list():
		new_models.append(str(m))
	
	# 2. Check if the backend list actually changed
	if _are_arrays_equal(available_models, new_models):
		return # No changes detected; bail out early to preserve current selection
	
	# 3. Update internal storage and rebuild the OptionButton items
	available_models = new_models
	
	%ModelButton.clear()
	for model in available_models:
		%ModelButton.add_item(model)
	
	# 4. Sync UI selection with current active backend model
	var current_backend_model = await BackendAPI.model()
	%ModelButton.selected = available_models.find(current_backend_model)


func _on_model_button_item_selected(index: int) -> void:
	if not await BackendAPI.model_set(%ModelButton.get_item_text(index)):
		%ModelButton.selected = -1


func _on_model_upate_timer_timeout() -> void:
	_update_models_button()


# Helper function to check if two typed arrays match exactly in size and order
func _are_arrays_equal(arr1: Array[String], arr2: Array[String]) -> bool:
	if arr1.size() != arr2.size():
		return false
	
	for i in range(arr1.size()):
		if arr1[i] != arr2[i]:
			return false
			
	return true
