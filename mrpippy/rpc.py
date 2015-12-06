

class RequestType(object):
    UseItem = 0 
    DropItem = 1 
    SetFavorite = 2 
    ToggleComponentFavorite = 3 
    SortInventory = 4 
    ToggleQuestActive = 5 
    SetCustomMapMarker = 6 
    RemoveCustomMapMarker = 7 
    CheckFastTravel = 8 
    FastTravel = 9 
    MoveLocalMap = 10
    ZoomLocalMap = 11
    ToggleRadioStation = 12
    RequestLocalMapSnapshot = 13
    ClearIdle = 14


class RPCManager(object):
	"""Manager for client RPC calls. Keeps track of what has been answered and
	executes callback(response dict) when it gets a response."""
	def __init__(self):
		self.next_id = 0
		self.outstanding = {} # maps id: callback

	def allocate_id(self):
		current = self.next_id
		self.next_id += 1
		return current

	def create_request(self, callback, request_type, *args):
		request = {
			'id': self.allocate_id(),
			'type': request_type,
			'args': args,
		}
		self.outstanding[request['id']] = callback
		return json.dumps(request)

	def recv(self, response):
		response = json.loads(response)
		if response['id'] not in self.outstanding:
			raise ValueError("Response for unknown id {}: {}".format(response['id']), response)
		self.outstanding.pop(response['id'])(response)


class RPCServer(object):
	"""Helper for responding to RPC calls as the server.
	Automatically dispatches incoming requests to the appropriate method.
	Method defaults will return reasonable "no-ops" where applicable.
	It is intended that you override these with meaningful implementations.
	"""
	# map from RequestType to the method name
	DISPATCH = {
		UseItem: 'use_item',
		DropItem: 'drop_item',
		SetFavorite: 'set_favorite',
		ToggleComponentFavorite: 'toggle_component_favorite',
		SortInventory: 'sort_inventory',
		ToggleQuestActive: 'toggle_quest_active',
		SetCustomMapMarker: 'set_custom_map_marker',
		RemoveCustomMapMarker: 'remove_custom_map_marker',
		CheckFastTravel: 'check_fast_travel',
		FastTravel: 'fast_travel',
		MoveLocalMap: 'move_local_map',
		ZoomLocalMap: 'zoom_local_map',
		ToggleRadioStation: 'toggle_radio_station',
		RequestLocalMapSnapshot: 'request_local_map_snapshot',
		ClearIdle: 'clear_idle',
	}

	def get_response(self, request):
		request = json.loads(request)
		id = request.pop('id')
		method = getattr(self, self.DISPATCH[request['type']])
		response = (*request['args'])
		response['id'] = id
		return response

	# TODO
