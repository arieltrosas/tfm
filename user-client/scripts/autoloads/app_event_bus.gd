extends Node

# Lifecycle
@warning_ignore("unused_signal")
signal backend_ready
@warning_ignore("unused_signal")
signal backend_events_connected
@warning_ignore("unused_signal")
signal backend_events_disconnected

# Workspace
@warning_ignore("unused_signal")
signal workspace_files_changed(files: Array)
@warning_ignore("unused_signal")
signal workspace_file_added(file_id: StringName, path: String)
@warning_ignore("unused_signal")
signal workspace_file_removed(file_id: StringName)

# Volume
@warning_ignore("unused_signal")
signal volume_changed(volume: Variant)

# Chat / models
@warning_ignore("unused_signal")
signal chat_response_received(text: String)
@warning_ignore("unused_signal")
signal models_changed(models: Array[String])
