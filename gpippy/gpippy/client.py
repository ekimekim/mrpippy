
from gevent.event import AsyncResult
import gevent

from mrpippy import ClientConnection, RPCManager, MessageType
from mrpippy.connection import ClientConnectionFromSocket

from common import Service


class ItemAppearsNotUsed(Exception):
	"""Raised when you try to use an item, but it appears to not actually happen."""
	def __init__(self, item, timeout, extra=None):
		self.item = item
		self.timeout = timeout
		self.extra = extra

	def __str__(self):
		if self.extra:
			return "Item {self.item} may have not been used: {self.extra}".format(self=self)
		return "Item {self.item} did not appear to have been used after {self.timeout} seconds".format(self=self)


class Client(Service):
	def __init__(self, host=None, port=27000, sock=None, on_update=None, on_close=None):
		"""on_update is an optional callback that is called with a list of updated values on DATA_UPDATE.
		Of host, port, sock, the following combinations can be given:
			port only: Listen on port and use the first peer that connects
			host, port: Connect to host, port
			sock only: Use given socket
		"""
		if sock:
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
		updates = []
		for n, update in enumerate(self.pipdata.decode_and_update(payload)):
			# since payload may be very large, give other greenlets a chance to run
			if n % 100 == 0:
				gevent.idle(0)
			updates.append(update)
		for callback in self.update_callbacks:
			callback(updates)

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

	def use_item(self, item, timeout=0):
		"""Use an item. If timeout is non-zero, wait up to timeout seconds trying to spot
		our item being "used" (ie. for an equippable, watch for it becoming equipped).
		Note this won't work for all items. If we could potentially spot it being used, and we don't
		within the timeout, raises a ItemAppearsNotUsed.
		"""
		handle_id = item.handle_id
		inventory = item.inventory
		self.do_rpc(handle_id, inventory.version)

		if not timeout:
			return

		if item in inventory.apparel + inventory.weapons:
			item_type = 'equip'
			target_state = not item.equipped
		elif item in inventory.aid:
			item_type = 'consume'
			target_quantity = item.count - 1
		else:
			return # can't see effects of use

		done = AsyncResult()

		# XXX if inventory version increases and we don't see the change, it must have failed?

		def _use_item_check(updates):
			found = [i for i in Inventory(self.pipdata).items if i.handle_id == handle_id]
			if len(found) > 1:
				done.set('Found multiple copies of same item?')
				return
			if found:
				item, = found

			quantity = item.count if found else 0
			if item_type == 'consume' and quantity == target_quantity:
				done.set(None)

			if not found:
				done.set(('Item no longer exists')

			if item_type == 'equip' and target_state == item.equipped:
				done.set(None)

		try:
			self.update_callbacks.add(_use_item_check)
			error = done.get(timeout)
		except gevent.Timeout:
			raise ItemAppearsNotUsed(item, timeout)
		finally:
			self.update_callbacks.discard(_use_item_check)

		if error:
			raise ItemAppearsNotUsed(item, timeout, error)
