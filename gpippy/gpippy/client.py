
import gevent

from mrpippy import ClientConnection, RPCManager, MessageType

from common import Service


def _do_rpc(name):
	"""Generates a method that calls self.do_rpc with the named method on self.rpc,
	eg. _do_rpc('foo')(self, *args) -> do_rpc(self, self.rpc.foo, *args)
	"""
	def generated(self, *args):
		return self.do_rpc(getattr(self.rpc, name), *args)
	generated.__name__ = name
	return generated


class Client(Service):
	def __init__(self, host, port=27000, on_update=None):
		"""on_update is an optional callback that is called with an updated value on DATA_UPDATE"""
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
		for n, update in enumerate(self.pipdata.decode_and_update(payload)):
			for callback in self.update_callbacks:
				callback(update)
			# since payload may be very large, give other greenlets a chance to run
			if n % 100 == 0:
				gevent.idle(0)

	def do_rpc(self, method, *args, **kwargs):
		block = kwargs.get('block', True)
		if kwargs:
			raise ValueError("Unexpected kwargs: {}".format(kwargs))
		result = AsyncResult()
		request = method(lambda v: result.set(v), *args)
		self.send(MessageType.COMMAND, request)
		self.log.info("Send RPC: {}{}".format(method, args))
		return result.get()

	use_item = _do_rpc('use_item')
