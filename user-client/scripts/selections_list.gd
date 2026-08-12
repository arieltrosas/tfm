class_name SelectionsList extends PanelContainer

const SelectionsListItemScn = preload("res://scenes/ui/SelectionsListItem.tscn")

var selections: Dictionary[String, SelectionsListItem] = {}


func _ready() -> void:
	AppEventBus.selections_changed.connect(_on_selections_changed)


func _add_item(id: String) -> void:
	if not id or id in selections:
		return
	
	var item: SelectionsListItem = SelectionsListItemScn.instantiate()
	item.id = id
	selections[id] = item
	
	%ItemList.add_child(item)


func _remove_item(id: String) -> void:
	if not id or id not in selections:
		return

	var item: SelectionsListItem = selections[id]
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
