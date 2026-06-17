extends Node

signal backend_ready
signal remote_event(event_type: String, payload: Dictionary)
signal events_connected
signal events_disconnected

const EVENT_RECONNECT_DELAY_SEC := 2.0

var backend_pid: int = -1
var backend_port: int = 8000

var _event_client: HTTPClient
var _event_buffer: String = ""
var _events_active: bool = false
var _reconnect_scheduled: bool = false


## NODE OVERRIDES

func _ready() -> void:
	get_tree().set_auto_accept_quit(false)
	await _launch_backend()
	await _set_default_model()
	backend_ready.emit()
	_start_event_stream()


func _process(_delta: float) -> void:
	if not _events_active or _event_client == null:
		return

	_event_client.poll()

	match _event_client.get_status():
		HTTPClient.STATUS_BODY:
			var chunk := _event_client.read_response_body_chunk()
			if chunk.size() > 0:
				_event_buffer += chunk.get_string_from_utf8()
				_parse_sse_buffer()
		HTTPClient.STATUS_CONNECTED, HTTPClient.STATUS_CONNECTING, HTTPClient.STATUS_RESOLVING, HTTPClient.STATUS_REQUESTING:
			pass
		_:
			_handle_event_stream_lost()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		_stop_event_stream()
		if backend_pid != -1:
			await shutdown()
		get_tree().quit()


## API ENDPOINTS

# app state

func get_app_state() -> Dictionary:
	var response = await _send_request("/state")
	if _backend_error(response):
		_print_backend_error("/state", response)
		return {}
	return response["body"]


# selection volume

func volume_get() -> Variant:
	var response = await _send_request("/volume/get")
	if _backend_error(response):
		_print_backend_error("/volume/get", response)
		return null
	return parse_aabb(response["body"].get("volume"))


func volume_set(aabb: Variant) -> bool:
	var volume_payload = null
	if aabb is AABB:
		volume_payload = {
			"x": aabb.position.x, "y": aabb.position.y, "z": aabb.position.z,
			"w": aabb.size.x, "h": aabb.size.y, "d": aabb.size.z,
		}
	var response = await _send_request("/volume/set", HTTPClient.METHOD_POST, JSON.stringify({"volume": volume_payload}))
	if _backend_error(response):
		_print_backend_error("/volume/set", response)
		return false
	return true


# chat

func chat(msg: String) -> String:
	var response = await _send_request("/chat", HTTPClient.METHOD_POST, JSON.stringify({"query": msg}))
	if _backend_error(response):
		_print_backend_error("/chat", response)
		return "Something went wrong"
	return response["body"].get("response", "Something went wrong")


# llm connection

func connect_ollama(host: String = "", key: String = "") -> bool:
	var body := {}
	if host != "":
		body["host"] = host
	if key != "":
		body["key"] = key
	var response = await _send_request("/connect/ollama", HTTPClient.METHOD_POST, JSON.stringify(body))
	if _backend_error(response):
		_print_backend_error("/connect/ollama", response)
		return false
	return true


func connect_openai(base_url: String, api_key: String) -> bool:
	var response = await _send_request(
		"/connect/openai",
		HTTPClient.METHOD_POST,
		JSON.stringify({"base_url": base_url, "api_key": api_key})
	)
	if _backend_error(response):
		_print_backend_error("/connect/openai", response)
		return false
	return true


# health

func health() -> bool:
	var response = await _send_request("/health")
	if _backend_error(response):
		return false
	return response["body"].get("status", "") == "healthy"


# workspace

func workspace() -> String:
	var response = await _send_request("/workspace")
	if _backend_error(response):
		_print_backend_error("/workspace", response)
		return ""
	return response["body"].get("ws_path", "")


func workspace_files() -> Array[String]:
	var response = await _send_request("/workspace/files")
	if _backend_error(response):
		_print_backend_error("/workspace/files", response)
		return []
	var files: Array[String] = []
	for entry in response["body"].get("files", []):
		if entry is Dictionary:
			files.append(entry.get("name", ""))
		else:
			files.append(str(entry))
	return files


func workspace_upload(file_paths: Array[String]) -> Dictionary:
	var response = await _send_request(
		"/workspace/upload",
		HTTPClient.METHOD_POST,
		JSON.stringify({"file_paths": file_paths})
	)
	if _backend_error(response):
		_print_backend_error("/workspace/upload", response)
		return {}
	return response["body"].get("results", {})


func workspace_download(file_name: String, download_path: String) -> Dictionary:
	var payload := {
		"file_name": file_name,
		"download_path": download_path
	}
	var response = await _send_request(
		"/workspace/download",
		HTTPClient.METHOD_POST,
		JSON.stringify(payload)
	)
	if _backend_error(response):
		_print_backend_error("/workspace/download", response)
		return {}
	return response["body"]


func workspace_remove(files: Array[String]) -> Dictionary:
	var response = await _send_request(
		"/workspace/remove",
		HTTPClient.METHOD_DELETE,
		JSON.stringify({"files": files})
	)
	if _backend_error(response):
		_print_backend_error("/workspace/remove", response)
		return {}
	return response["body"].get("results", {})


# model

func model() -> String:
	var response = await _send_request("/model")
	if _backend_error(response):
		return ""
	return response["body"].get("model", "")


func model_list() -> Array[String]:
	var response = await _send_request("/model/list")
	if _backend_error(response):
		return []
	var models: Array[String]
	models.assign(response["body"].get("models", []))
	return models


func model_set(model_name: String) -> bool:
	var response = await _send_request("/model/set", HTTPClient.METHOD_POST, JSON.stringify({"model": model_name}))
	if _backend_error(response):
		return false
	return true


# shutdown

func shutdown() -> void:
	_stop_event_stream()
	await _send_request("/shutdown", HTTPClient.METHOD_POST)


# geometry

func geometry_mesh_supported(file_path: String) -> bool:
	var response = await _send_request(
		"/geometry/mesh/supported", 
		HTTPClient.METHOD_POST, 
		JSON.stringify({"file_path": file_path})
	)
	if _backend_error(response):
		_print_backend_error("/geometry/mesh/supported", response)
		return false
	return response["body"].get("is_supported", false)


func geometry_point_cloud_supported(file_path: String) -> bool:
	var response = await _send_request(
		"/geometry/point-cloud/supported", 
		HTTPClient.METHOD_POST, 
		JSON.stringify({"file_path": file_path})
	)
	if _backend_error(response):
		_print_backend_error("/geometry/point-cloud/supported", response)
		return false
	return response["body"].get("is_supported", false)


func geometry_mesh_convert(src_path: String, dst_path: String) -> void:
	var payload := {
		"src_path": src_path,
		"dst_path": dst_path
	}
	var response = await _send_request(
		"/geometry/mesh/convert", 
		HTTPClient.METHOD_POST, 
		JSON.stringify(payload)
	)
	if _backend_error(response):
		_print_backend_error("/geometry/mesh/convert", response)


## HELPERS

func _launch_backend() -> void:
	if OS.is_debug_build():
		return

	var port_file = ProjectSettings.globalize_path("user://port")
	if FileAccess.file_exists(port_file):
		DirAccess.remove_absolute(port_file)

	backend_pid = OS.create_process(_get_backend_binary(), ["client", port_file])
	if backend_pid == -1:
		printerr("Could not launch backend process")

	while not FileAccess.file_exists(port_file):
		await get_tree().create_timer(0.25).timeout

	var file = FileAccess.open(port_file, FileAccess.READ)
	if file and file.is_open():
		backend_port = int(file.get_as_text())

	while not await health():
		await get_tree().create_timer(0.25).timeout


func _set_default_model() -> void:
	var current_model = await self.model()
	if not current_model:
		var models = await self.model_list()
		if models:
			await self.model_set(models[0])


func _get_backend_binary() -> String:
	var exe_dir = OS.get_executable_path().get_base_dir()
	match OS.get_name():
		"Windows":
			return exe_dir.path_join("backend.exe")
		"MacOS", "Linux":
			return exe_dir.path_join("backend")
	return exe_dir.path_join("backend")


func _start_event_stream() -> void:
	_connect_event_stream()


func _connect_event_stream() -> void:
	if backend_port == 0:
		printerr("BackendAPI Error: Cannot subscribe to events without a backend port")
		return

	_stop_event_stream()
	_event_client = HTTPClient.new()
	var err := _event_client.connect_to_host("127.0.0.1", backend_port)
	if err != OK:
		printerr("BackendAPI Error: Failed to connect event stream: ", err)
		_schedule_event_reconnect()
		return

	while _event_client.get_status() in [HTTPClient.STATUS_CONNECTING, HTTPClient.STATUS_RESOLVING]:
		_event_client.poll()
		await get_tree().process_frame

	if _event_client.get_status() != HTTPClient.STATUS_CONNECTED:
		printerr("BackendAPI Error: Event stream connection failed with status ", _event_client.get_status())
		_event_client = null
		_schedule_event_reconnect()
		return

	var headers := PackedStringArray(["Accept: text/event-stream"])
	err = _event_client.request(HTTPClient.METHOD_GET, "/events", headers)
	if err != OK:
		printerr("BackendAPI Error: Failed to request event stream: ", err)
		_event_client = null
		_schedule_event_reconnect()
		return

	while _event_client.get_status() == HTTPClient.STATUS_REQUESTING:
		_event_client.poll()
		await get_tree().process_frame

	if _event_client.get_status() != HTTPClient.STATUS_BODY:
		printerr("BackendAPI Error: Event stream request failed with status ", _event_client.get_status())
		_event_client = null
		_schedule_event_reconnect()
		return

	_event_buffer = ""
	_events_active = true
	set_process(true)
	events_connected.emit()


func _stop_event_stream() -> void:
	_events_active = false
	_reconnect_scheduled = false
	set_process(false)
	_event_buffer = ""
	if _event_client != null:
		_event_client.close()
		_event_client = null


func _handle_event_stream_lost() -> void:
	if not _events_active:
		return
	_stop_event_stream()
	events_disconnected.emit()
	_schedule_event_reconnect()


func _schedule_event_reconnect() -> void:
	if _reconnect_scheduled:
		return
	_reconnect_scheduled = true
	await get_tree().create_timer(EVENT_RECONNECT_DELAY_SEC).timeout
	_reconnect_scheduled = false
	_connect_event_stream()


func _parse_sse_buffer() -> void:
	while true:
		var boundary := _event_buffer.find("\n\n")
		if boundary == -1:
			break
		var block := _event_buffer.substr(0, boundary)
		_event_buffer = _event_buffer.substr(boundary + 2)
		_process_sse_block(block)


func _process_sse_block(block: String) -> void:
	for line in block.split("\n"):
		if line.begins_with(":"):
			continue
		if not line.begins_with("data: "):
			continue
		var parsed = JSON.parse_string(line.substr(6))
		if parsed is Dictionary:
			_dispatch_event(parsed)


func _dispatch_event(event: Dictionary) -> void:
	remote_event.emit(event.get("type", ""), event.get("payload", {}))


func _send_request(endpoint: String, method: HTTPClient.Method = HTTPClient.METHOD_GET, body: String = "") -> Dictionary:
	if backend_port == 0:
		return {"status": "error", "code": 0, "message": ""}

	var http_node = HTTPRequest.new()
	add_child(http_node)
	var url = "http://127.0.0.1:%d%s" % [backend_port, endpoint]
	var error = http_node.request(url, ["Content-Type: application/json"], method, body)
	if error != OK:
		remove_child(http_node)
		http_node.queue_free()
		return {"status": "error", "code": 0, "message": ""}

	var result = await http_node.request_completed
	var response_code = result[1]
	var response_body = result[3].get_string_from_utf8()
	remove_child(http_node)
	http_node.queue_free()

	if 200 <= response_code and response_code < 300:
		return {"status": "success", "body": JSON.parse_string(response_body)}
	return {"status": "error", "code": response_code, "message": response_body}


func _backend_error(response: Dictionary) -> bool:
	return response["status"] == "error"


func _print_backend_error(endpoint: String, response: Dictionary) -> void:
	printerr("BackendAPI Error at %s: Error %s %s" % [endpoint, response["code"], response["message"]])


func parse_aabb(dict: Variant) -> Variant:
	if dict == null or not (dict is Dictionary):
		return null
	var pos = Vector3(dict.get("x", 0.0), dict.get("y", 0.0), dict.get("z", 0.0))
	var size = Vector3(dict.get("w", 0.0), dict.get("h", 0.0), dict.get("d", 0.0))
	return AABB(pos, size)
