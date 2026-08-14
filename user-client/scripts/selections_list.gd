class_name SelectionsList extends PanelContainer

const SelectionsListItemScn = preload("res://scenes/ui/SelectionsListItem.tscn")

var selections: Dictionary[String, SelectionsListItem] = {}
var _rename_pending: Dictionary[SelectionsListItem, bool] = {}


func _ready() -> void:
	AppEventBus.selections_changed.connect(_on_selections_changed)


func _add_item(id: String) -> void:
	if not id or id in selections:
		return
	
	var item: SelectionsListItem = SelectionsListItemScn.instantiate()
	item.id = id
	item.name_changed.connect(_on_item_name_changed.bind(item))
	selections[id] = item
	
	%ItemList.add_child(item)


func _remove_item(id: String) -> void:
	if not id or id not in selections:
		return

	var item: SelectionsListItem = selections[id]
	_rename_pending.erase(item)
	selections.erase(id)
	%ItemList.remove_child(item)
	item.queue_free()


func _get_selected_items() -> Array[String]:
	return selections.keys().filter(
		func(id: String): return selections[id].selected
	)


func _deselect_items() -> void:
	for id in selections:
		selections[id].selected = false


func _on_remove_pressed() -> void:
	var selected: Array[String] = _get_selected_items()
	for id in _get_selected_items():
		_remove_item(id)
	BackendAPI.selection_remove(selected)
	_deselect_items()


func _id_for_item(item: SelectionsListItem) -> String:
	for id in selections:
		if selections[id] == item:
			return id
	return ""


func _on_item_name_changed(_name: String, item: SelectionsListItem) -> void:
	if _rename_pending.get(item, false):
		return
	_rename_pending[item] = true
	await _flush_item_rename(item)
	_rename_pending.erase(item)


func _flush_item_rename(item: SelectionsListItem) -> void:
	while is_instance_valid(item):
		var old_id := _id_for_item(item)
		var new_id := item.id
		if not old_id or old_id == new_id or not new_id:
			return
		if new_id in selections:
			return

		selections.erase(old_id)
		selections[new_id] = item
		var ok := await BackendAPI.selection_rename(old_id, new_id)
		if ok:
			continue

		if _id_for_item(item) == new_id:
			selections.erase(new_id)
			selections[old_id] = item
		return


func _on_selections_changed(backend_selections: Dictionary) -> void:
	var back_ids: Array[String]; back_ids.assign(backend_selections.keys())
	var front_ids: Array[String]; front_ids.assign(selections.keys())
	
	var to_remove: Array[String] = front_ids.filter(
		func (id: String) -> bool:
			return id not in back_ids
	)
	var to_add: Array[String] = back_ids.filter(
		func (id: String) -> bool:
			return id not in front_ids
	)
	
	for id in to_remove:
		_remove_item(id)
	
	for id in to_add:
		_add_item(id)
