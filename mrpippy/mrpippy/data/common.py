
class Data(object):
	"""Base class for all objects based on gathered data values"""

	def __init__(self, value_or_manager):
		if isinstance(value_or_manager, DataManager):
			value_or_manager = self.from_manager(value_or_manager)
		self.root = value_or_manager

	def from_manager(self, manager):
		"""Override with a method that returns this object's root value"""
		raise ValueError("Can not instantiate {} from manager alone".format(type(self).__name__))

	@property
	def value(self):
		return self.root.value

	@property
	def manager(self):
		return self.root.manager
