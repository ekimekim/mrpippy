
import struct
import time


class Incomplete(Exception):
	pass


def eat(data, n):
	"""Take first n bytes of data and return (first n bytes, remainder).
	Raise Incomplete if not long enough."""
	if len(data) < n:
		raise Incomplete("Expected {} bytes, got {}".format(n, len(data)))
	return data[:n], data[n:]


def pack(spec, *values):
	return struct.pack('<' + spec, *values)


def unpack(spec, data, as_tuple=False):
	spec = '<' + spec
	length = struct.calcsize(spec)
	data, remaining = eat(data, length)
	results = struct.unpack(spec, data)
	if len(results) == 1 and not as_tuple:
		results, = results
	return results, remaining


def parse_string(data):
	if '\0' not in data:
		raise Incomplete("Expected nul byte not found")
	return data.split('\0', 1)


class Timer(object):
	def __init__(self, log, name):
		self.log = log
		self.name = name
	def __enter__(self):
		self.start = time.time()
		self.log.debug('Entering %s', name)
	def __exit__(self, *exc_info):
		self.log.info("Exiting %s, took %.4fs", name, time.time() - self.start)
