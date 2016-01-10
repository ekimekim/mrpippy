
from gevent.event import AsyncResult
import gevent

from mrpippy import ClientConnection, RPCManager, MessageType
from mrpippy.connection import ClientConnectionFromSocket

from common import Service


def _do_rpc(name):
	"""Generates a method that calls self.do_rpc with the named method on self.rpc,
	eg. _do_rpc('foo')(self, *args) -> do_rpc(self, self.rpc.foo, *args)
	"""
	def generated(self, *args, **kwargs):
		return self.do_rpc(getattr(self.rpc, name), *args, **kwargs)
	generated.__name__ = name
	return generated


class Client(Service):
	def __init__(self, host, port=27000, on_update=None, on_close=None, sock=None):
		"""on_update is an optional callback that is called with a list of updated values on DATA_UPDATE.
		You can either give (host, port) to connect to, or host=None to listen for an incoming connection,
		or sock=a socket object explicitly."""
		if sock is not None:
			self.conn = ClientConnectionFromSocket(sock)
		elif host is None:
			import socket
			l = socket.socket()
			l.bind(('0.0.0.0', 27000))
			l.listen(128)
			sock, a = l.accept()
			l.close()
			self.conn = ClientConnectionFromSocket(sock)
		else:
			self.conn = ClientConnection(host, port)
		self.rpc = RPCManager()
		self.update_callbacks = set()
		if on_update:
			self.update_callbacks.add(on_update)
		super(Client, self).__init__(on_close=on_close)

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
			# since payload may be very large, give other greenlets a chance to run
			if n % 100 == 0:
				gevent.idle(0)
		for callback in self.update_callbacks:
			callback(update)

	def do_rpc(self, method, *args, **kwargs):
		block = kwargs.pop('block', False)
		if kwargs:
			raise ValueError("Unexpected kwargs: {}".format(kwargs))
		if block:
			result = AsyncResult()
			request = method(*args, callback=lambda v: result.set(v))
		else:
			request = method(*args)
		self.send(MessageType.COMMAND, request)
		self.log.info("Send RPC: {}{}".format(method, args))
		if block:
			return result.get()

	use_item = _do_rpc('use_item')
