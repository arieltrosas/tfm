class_name WorkspaceService extends RefCounted

func upload_files(paths: Array[String]) -> void:
	await BackendAPI.workspace_upload(paths)


func remove_files(files: Array[String]) -> void:
	await BackendAPI.workspace_remove(files)


func download_file(file: String, destination: String) -> void:
	await BackendAPI.workspace_download(file, destination)
