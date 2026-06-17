class_name WorkspaceService extends RefCounted

func upload_files(local_paths: PackedStringArray) -> void:
	for path in local_paths:
		await BackendAPI.workspace_upload(path)


func remove_files(file_ids: Array[StringName]) -> void:
	for file_id in file_ids:
		await BackendAPI.workspace_remove(str(file_id))


func download_file(file_id: StringName, destination: String) -> void:
	BackendAPI.workspace_download(str(file_id), destination)
