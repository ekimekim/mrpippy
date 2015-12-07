
import errno
import functools
import logging
import socket

import gevent

from mrpippy import PipDataManager, MessageType


def close_on_error(fn):
	"""Decorator that calls self.close() if a method raises or returns"""
	@functools.wraps(fn)
	def _wrapper(self, *args, **kwargs):
		try:
			fn(self, *args, **kwargs)
		except Exception as ex:
			self.close(ex)
		else:
			self.close()


class Service(object):
	def __init__(self):
		"""Subclasses should set self.conn before calling super()"""
		self.group = gevent.pool.Group()
		self.log = logging.getLogger('gpippy.{}.{:x}'.format(type(self).__name__), id(self))

		self.pipdata = PipDataManager()
		self.send_queue = gevent.queue.Queue()
		self.closing = False
		self.finished = gevent.event.AsyncResult()

		self.group.spawn(self._send_loop)
		self.group.spawn(self._recv_loop)
		self.group.spawn(self._keepalive)

	@close_on_error
	def _send_loop(self):
		for message_type, payload in self.send_queue:
			try:
				self.log.debug("Sending message of type {}: {!r}".format(message_type, payload))
				self.conn.send(message_type, payload)
			except socket.error as ex:
				if ex.errno == errno.EPIPE:
					self.log.info("Peer closed connection")
					return
				raise

	@close_on_error
	def _recv_loop(self):
		while True:
			try:
				message_type, payload = self.conn.recv()
			except EOFError:
				self.log.info("Peer closed connection")
				return
			self.log.debug("Received message of type {}: {!r}".format(message_type, payload))
			self.process(message_type, payload)

	@close_on_error
	def _keepalive(self):
		# other sources suggest official game/app can get picky about sending too many keepalives?
		while True:
			gevent.sleep(self.KEEPALIVE_TIMEOUT)
			self.log.info("Sending keepalive")
			self.send(MessageType.KEEP_ALIVE, "")

	def close(self, ex=None):
		if self.closing:
			self.finished.get()

		self.closing = True
		self.log.info("Closing with error {}".format(ex))

		@gevent.spawn
		def _close():
			self.group.kill(block=True)
			self.conn.socket.close()
			if ex:
				self.finished.set_exception(ex)
			else:
				self.finished.set(None)

		_close.get()

	def wait(self):
		self.finished.get()

	def send(self, message_type, payload):
		self.send_queue.put((message_type, payload))

	def process(self, message_type, payload):
		"""Override this with behaviour upon message recieve.
		Note that this function is running in the recv_loop greenlet, so if you block
		then no more messages will be received."""
		raise NotImplementedError
