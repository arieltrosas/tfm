extends MarginContainer

@export var workspace_view: WorkspaceView
@export var viewer_view: ViewerView
@export var chat_view: ChatView
@export var auth_popup: PopupPanel
@export var info_popup: PopupPanel

var _workspace_service: WorkspaceService
var _chat_service: ChatService
var _auth_service: AuthService
var _bridge: BackendBridge


func _ready() -> void:
	_workspace_service = WorkspaceService.new()
	_chat_service = ChatService.new()
	_auth_service = AuthService.new()
	_bridge = BackendBridge.new()

	_bridge.install()

	_chat_service.setup()

	workspace_view.setup(_workspace_service)
	chat_view.setup(_chat_service)
	viewer_view.setup()

	AppEventBus.backend_ready.emit()
	await _chat_service.refresh_models()


func _on_auth_button_pressed() -> void:
	auth_popup.popup_centered()


func _on_info_popup_ok_pressed() -> void:
	info_popup.hide()


func _on_auth_popup_accept_pressed() -> void:
	var host_edit := auth_popup.get_node("MarginContainer/VBoxContainer/VBoxContainer/HostInput") as LineEdit
	var key_edit := auth_popup.get_node("MarginContainer/VBoxContainer/VBoxContainer/KeyInput") as LineEdit

	var host := host_edit.text
	var key := key_edit.text
	key_edit.text = ""

	var info := await _auth_service.connect_provider(host, key)

	info_popup.get_node("MarginContainer/VBoxContainer/Label").text = info
	auth_popup.hide()
	info_popup.popup_centered()


func _on_cancel_pressed() -> void:
	auth_popup.hide()
