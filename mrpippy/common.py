

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


def unpack(spec, data):
    spec = '<' + spec
    length = struct.calcsize(spec)
    data, remaining = eat(data, length)
    return struct.unpack(spec, data), remaining


def parse_string(data):
	if '\0' not in data:
		raise Incomplete("Expected nul byte not found")
    return data.split('\0', 1)
