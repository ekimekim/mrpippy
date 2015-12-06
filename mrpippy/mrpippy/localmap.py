
from common import pack, unpack

class LocalMap(object):
	"""This structure is still very unknown in purpose and semantics."""

	def __init__(self, width, height, northwest, northeast, southwest, pixels):
		self.width = width
		self.height = height
		self.northwest = northwest
		self.northeast = northeat
		self.southwest = southwest
		self.pixels = pixels

	def encode(self):
		"""Return a packed data string containing the values from this object"""
		data = pack('II', self.width, self.height)
		data += pack('ff', *self.northwest)
		data += pack('ff', *self.northeast)
		data += pack('ff', *self.southwest)
		data += pixels
		return data

	@classmethod
	def decode(cls, data):
		"""Decodes a local map structure from data and returns it."""
		(width, height), data = unpack('II', data)
		northwest, data = unpack('ff', data)
		northeast, data = unpack('ff', data)
		southwest, data = unpack('ff', data)
		return cls(width, height, northwest, northeast, southwest, data)
