
from itertools import count

from common import pack, unpack, parse_string


class ValueType(object):
	BOOL = 0 
	INT_8 = 1 
	UINT_8 = 2 
	INT_32 = 3 
	UINT_32 = 4 
	FLOAT = 5 
	STRING = 6 
	ARRAY = 7 
	OBJECT = 8 


class PipValue(object):
	# maps applicable primitive value types to struct letters
	TYPE_MAP = {
		ValueType.BOOL: '?',
		ValueType.INT_8: 'b',
		ValueType.UINT_8: 'B',
		ValueType.INT_32: 'i',
		ValueType.UINT_32: 'I',
		ValueType.FLOAT: 'f',
	}

	def __init__(self, manager, value_type, value, id=None):
		"""Value must match value_type.
		If id is not given, allocates one.
		ARRAY type should be a list of value ids.
		OBJECT type should be a dict {key: value id}"""
		self.manager = manager
		self.id = id or manager.next_id()
		if self.id in self.manager.id_map:
			raise ValueError("PipValue with id {} already exists: {}".format(self.id, self.manager.id_map[self.id]))
		self.manager.id_map[self.id] = self
		self.value_type = value_type
		self._value = value

	def __repr__(self):
		return "<{cls.__name__} {self.id}={self.value}>".format(cls=type(self), self=self)

	@property
	def value(self):
		"""Return the actual decoded value with all subvalues dereferenced"""
		if self.value_type == ValueType.OBJECT:
			return {key: self.manager.id_map[value_id].value for key, value_id in self._value.items()}
		if self.value_type == ValueType.ARRAY:
			return [self.manager.id_map[value_id].value for value_id in self._value]
		return self._value

	def update(self, value):
		"""Update this id with a new value as returned from decode()"""
		if self.value_type == ValueType.OBJECT:
			added, removed = value
			self._value = {key: value_id for key, value_id in self._value.items() if value_id not in removed}
			# NOTE: Even though we are orphaning value_ids here, there is no cleanup, causing a mem leak
			self._value.update(added)
		else:
			self._value = value

	def __getitem__(self, item):
		"""Get the PipValue for a subitem of an ARRAY or OBJECT"""
		return self.manager.id_map[self._value[item]]

	def __iter__(self):
		"""Iterate over an ARRAY or OBJECT. Note ARRAYs return PipValue()s"""
		for item in self._value:
			if self.value_type == ValueType.ARRAY:
				item = self.manager.id_map[item]
			yield item

	def encode(self, prev_state={}):
		"""Return the encoded string for a DATA_UPDATE of this object's current state.
		For OBJECTs, optionally include the previously sent state as OBJECT updates are
		diffs, not absolute values. This state should be a dict {key: id}"""
		data = pack('BI', self.value_type, self.id)
		if self.value_type in self.TYPE_MAP:
			data += pack(self.TYPE_MAP[self.value_type], self._value)
		elif self.value_type == ValueType.STRING:
			data += self._value + '\0'
		elif self.value_type == ValueType.ARRAY:
			data += pack('H', len(self._value)) + pack(len(self._value) * 'I', *self._value)
		elif self.value_type == ValueType.OBJECT:
			removed = [value_id for key, value_id in prev_state.items()
			           if self._value.get(key) != value_id]
			added = {key: value_id for key, value_id in self._value.items()
			         if prev_state.get(key) != value_id}
			data += pack('H', len(added))
			for key, value_id in added.items():
				data += pack('I', value_id) + key + '\0'
			data += pack('H', len(removed)) + pack(len(removed) * 'I', *removed)
		return data

	@classmethod
	def decode(cls, value_type, data):
		"""Decode value from data according to value_type, return (value, remaining data).
		Note the decoded value for objects is (added, deleted) where added is a list of (key, value_id)
		and deleted is just a list of value_id."""
		if value_type in cls.TYPE_MAP:
			value, data = unpack(cls.TYPE_MAP[value_type], data)
		elif value_type == ValueType.STRING:
			value, data = parse_string(data)
		elif value_type == ValueType.ARRAY:
			# array is uint16 length, elements are uint32 ids
			length, data = unpack('H', data)
			value, data = unpack(length * 'I', data)
		elif value_type == ValueType.OBJECT:
			# object is two parts:
			#     added: (uint16 length, elements are (uint32 id, string key))
			#     removed: uint16, uint32 id
			length, data = unpack('H', data)
			added = {}
			for x in range(length):
				id, data = unpack('I', data)
				key, data = parse_string(data)
				added[key] = id
			length, data = unpack('H', data)
			removed, data = unpack(length * 'I', data)
			value = added, removed
		else:
			raise ValueError("Unknown value type {!r}".format(value_type))
		return value, data


class PipDataManager(object):
	def __init__(self):
		self.id_map = {}

	def encode(self, *values, **kwargs):
		"""Takes a list of PipValues, and encodes them all into one DATA_UPDATE payload.
		If kwarg recursive=True, also include all PipValues that are children of the given values.
		A new connection should always start with manager.encode_all(manager.root, recursive=True).
		"""
		recursive = kwargs.pop('recursive', False)
		if kwargs:
			raise ValueError("Unexpected kwargs: {}".format(kwargs))

		if recursive:
			original_values = values
			values = []
			def add(value):
				# if already present, move to front
				if value in values:
					values.remove(value)
				values.insert(0, value)
				if value.value_type == ValueType.ARRAY:
					ids = value.raw_value
				elif value.value_type == ValueType.OBJECT:
					ids = value.raw_value.values()
				else:
					return
				for id in ids:
					add(self.id_map[id])
			for value in original_values:
				add(value)

		return ''.join(value.encode() for value in values)

	def decode(self, data):
		"""Decode a DATA_UPDATE message, returning a list of (id, value_type, value) updates."""
		results = []
		while data:
			(value_type, id), data = unpack('BI', data)
			value, data = PipValue.decode(value_type, data)
			results.append((id, value_type, value))
		return results

	def decode_and_update(self, data):
		"""Decode a DATA_UPDATE message, create or update the pip values, and return them as a list.
		To update a value manually, you should instead manipulate the PipValue directly."""
		results = []
		for id, value_type, value in self.decode(data):
			if id in self.id_map:
				pipvalue = self.id_map[id]
				if pipvalue.value_type != value_type:
					raise ValueError("Data update has type {value_type!r}, but existing record {pipvalue} has type {pipvalue.value_type!r}".format(
						value_type=value_type,
						pipvalue=pipvalue,
					))
				pipvalue.update(value)
			else:
				if value_type == ValueType.OBJECT:
					value, removed = value
					if removed:
						raise ValueError("Got non-empty removed list for new id {}".format(id))
				pipvalue = PipValue(self, value_type, value, id)
			results.append(pipvalue)
		return results

	def next_id(self):
		"""Get next lowest available id number"""
		next_id = (id for id in count() if id not in self.id_map).next()
		if next_id >= 2**16:
			raise ValueError("Out of ids")

	@property
	def root(self):
		"""Return the root node, or None if it isn't defined yet"""
		return self.id_map.get(0)
