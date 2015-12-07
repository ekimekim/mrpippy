
from mrpippy import ClientConnection, RPCManager, MessageType

from common import Service


class Client(Service):
	def __init__(self, host, port=27000, on_update=None):
		"""on_update is an optional callback that is called with a list of updated values on DATA_UPDATE"""
		self.conn = ClientConnection(host, port)
		self.rpc = RPCManager()
		self.update_callbacks = set()
		if on_update:
			self.update_callbacks.add(on_update)
		super(Client, self).__init__()

	def process(self, message_type, payload):
		IGNORE = lambda payload: None
		DISPATCH = {
			MessageType.KEEP_ALIVE: IGNORE,
			MessageType.DATA_UPDATE: self.data_update,
			MessageType.LOCAL_MAP_UPDATE: IGNORE, # we don't understand maps yet
			MessageType.COMMAND_RESULT: self.rpc.recv,
		}

		if message_type not in DISPATCH:
			self.log.warning("Unexpected message type {}, ignoring".format(message_type))
			return

		DISPATCH[message_type](payload)

	def data_update(self, payload):
		updated = self.pipdata.decode_and_update(payload)
		for callback in self.update_callbacks:
			callback(updated)
