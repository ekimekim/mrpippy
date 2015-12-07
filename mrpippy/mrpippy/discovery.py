
from contextlib import closing
from select import select
import json
import socket
import time


def discover(timeout=1, repeats=5, port=28000, allow_busy=False):
	"""Uses UDP broadcast to find pip boy app hosts on the local network.
	Returns a set of (ip, machine_type).
	if allow_busy=True, also include replies that indicated server was present but busy.
	timeout is how long to wait for responses.
	repeats is how many broadcast packets to send. This makes the message (and replies) more likely
	to make it through despite packet loss."""
	with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)) as sock:
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
		for x in range(repeats):
			sock.sendto(json.dumps({'cmd': 'autodiscover'}), ('255.255.255.255', 28000))
		results = set()
		start = time.time()
		while True:
			time_left = start + timeout - time.time()
			if time_left <= 0:
				break
			r, w, x = select([sock], [], [], time_left)
			if r:
				assert r == [sock]
				message = sock.recvfrom(1024)
				try:
					message = json.loads(message)
				except (ValueError, UnicodeDecodeError):
					continue # malformed message, ignore it
				if not isinstance(message, dict):
					continue # not a json object, ignore it
				if any(key not in message for key in ['MachineType', 'addr', 'IsBusy']):
					continue # missing required keys, ignore it
				if message['IsBusy'] and not allow_busy:
					continue # server is busy, ignore it
				results.add((message['addr'], message['MachineType']))
	return results


class DiscoverServer(object):
	def __init__(self, addr, machine_type='PC', port=28000, busy=False):
		"""addr is the tcp addr to advertise connections for"""
		self.addr = addr
		self.machine_type = machine_type
		self.busy = busy
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
		self.socket.bind(('255.255.255.255', port))

	def serve_one(self):
		msg, addr = self.socket.recvfrom(1024)
		try:
			msg = json.loads(msg)
		except Exception:
			continue # malformed msg
		if msg != {'cmd': 'autodiscover'}:
			continue # ignore bad msg
		response = {
			'addr': self.addr,
			'MachineType': self.machine_type,
			'IsBusy': self.busy,
		}
		self.socket.sendto(json.dumps(response), addr)

	def serve_forever(self):
		while True:
			self.serve_one()
