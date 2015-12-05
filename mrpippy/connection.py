
import json
import socket

from common import Incomplete, eat, pack, unpack


class MessageType(object):
	KEEP_ALIVE = 0
	CONNECTION_ACCEPTED = 1
	CONNECTION_REFUSED = 2
	DATA_UPDATE = 3
	LOCAL_MAP_UPDATE = 4
	COMMAND = 5
	COMMAND_RESULT = 6


class ConnectionRefused(Exception):
	pass


class Connection(object):
	socket = NotImplemented
	version = 'unknown'
	language = 'unknown'

	def __init__(self):
		"""Shared init code. Subclasses should set self.socket before calling super."""
		self.buffer = ''
		self.handshake()

	def handshake(self):
		"""Specific code for client and server during initial handshake
		(accept or reject connection) goes here."""
		raise NotImplementedError

	@classmethod
	def encode(cls, message_type, payload):
		"""Return encoded bytes for a message of given type with given encoded bytes payload"""
		return pack('IB', len(payload), message_type) + payload

	@classmethod
	def decode(cls, data):
		"""Decode message from data and return (message_type, payload, remaining data),
		or raise Incomplete if more data is needed to complete a message."""
		(length, message_type), data = unpack('IB', data)
		payload, data = eat(data, length)
		return message_type, payload, data

	def send(self, message_type, payload):
		"""Send a message on the connection"""
		self.socket.sendall(self.encode(message_type, payload))

	def recv(self):
		"""Block until the next message can be parsed, and return (message_type, payload).
		Will raise EOFError if socket is closed."""
		while True:
			try:
				message_type, payload, self.buffer = self.decode(self.buffer)
				return message_type, payload
			except Incomplete:
				pass
			data = self.socket.recv(4096)
			if not data:
				raise EOFError
			self.buffer += data

	def send_keepalive(self):
		self.send(MessageType.KEEP_ALIVE, "")


class ClientConnection(Connection):
	def __init__(self, host, port=27000):
		self.socket = socket.socket()
		self.socket.connect((host, port))
		super(ClientConnection, self).__init__()

	def handshake(self):
		message_type, payload = self.recv()
		if message_type == MessageType.CONNECTION_REFUSED:
			raise ConnectionRefused("The server responded, but was not ready. Refusal payload: {!r}".format(payload))
		if message_type != MessageType.CONNECTION_ACCEPTED:
			raise ValueError("Expected server to open with type CONNECTION_ACCEPTED({}), got type {}: {!r}".format(
				MessageType.CONNECTION_ACCEPTED, message_type, payload,
			))
		payload = json.loads(payload)
		self.version = payload['version']
		self.language = payload['lang']


class ServerConnection(Connection):
	def __init__(self, sock, version=None, language=None):
		"""Takes an already connected socket, as returned by accept()"""
		self.socket = sock
		if version is not None:
			self.version = version
		if language is not None:
			self.language = language
		super(ServerConnection, self).__init__()

	def handshake(self):
		self.send(MessageType.CONNECTION_ACCEPTED, json.dumps({
			'version': self.version,
			'lang': self.language,
		}))

