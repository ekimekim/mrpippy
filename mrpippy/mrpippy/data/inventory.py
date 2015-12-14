
from common import Data

ITEM_TYPES = {
	'29': 'Apparel',
	'30': 'Notes/Magazines',
	'35': 'Misc/Junk',
	'43': 'Weapons',
	'44': 'Ammo',
	'47': 'Keys/Passwords',
	'48': 'Aid',
	'50': 'Holotapes',
}

EQUIP_STATES = {
	0: 'Not Equipped',
	1: 'Clothing',
	3: 'Grenade',
	4: 'Weapon',
}


class Inventory(Data):

	def from_manager(self, manager):
		return manager.root['Inventory']

	@property
	def stimpak(self):
		"""Returns the Item() corresponding to stimpaks, or None"""
		if not self.root.value['stimpakObjectIDIsValid']:
			return
		return Item(self.manager.id_map[self.root.value['stimpakObjectID']])

	@property
	def radaway(self):
		"""Returns the Item() corresponding to radaways, or None"""
		if not self.root.value['radawayObjectIDIsValid']:
			return
		return Item(self.manager.id_map[self.root.value['radawayObjectID']])

	@property
	def items(self):
		"""Returns a list of all Item()s in the inventory"""
		return sum((self._items(k) for k in ITEM_TYPES), [])

	@property
	def apparel(self):
		return self._items('29')

	@property
	def notes(self):
		return self._items('30')

	@property
	def misc(self):
		return self._items('35')

	@property
	def weapons(self):
		return self._items('43')

	@property
	def ammo(self):
		return self._items('44')

	@property
	def keys(self):
		return self._items('47')

	@property
	def aid(self):
		return self._items('48')

	@property
	def holotapes(self):
		return self._items('50')

	def _items(self, item_type):
		return [Item(value) for value in self.root[item_type]]

	@property
	def version(self):
		return self.root.value['Version']

	@property
	def weapon(self):
		"""Returns the currently equipped weapon, or None"""
		weapons = self._find_equip(4)
		if not weapons:
			return
		weapon, = weapons
		return weapon

	@property
	def grenade(self):
		"""Returns the currently equipped grenade, or None"""
		grenades = self._find_equip(3)
		if not grenades:
			return
		grenade, = grenades
		return grenade

	@property
	def wearing(self):
		"""Returns a list of equipped clothing"""
		return self._find_equip(1)

	def _find_equip(self, state):
		return [item for item in self.items if item.value['equipState'] == state]


class Item(Data):
	"""Represents one record in the item list. Could be multiple items of the same type."""

	def __repr__(self):
		return "<{cls.__name__} {self.count}x {self.name!r}>".format(self=self, cls=type(self))
	__str__ = __repr__

	@property
	def name(self):
		return self.root.value['text']

	@property
	def count(self):
		return self.root.value["count"]

	def _find_info(self, **criteria):
		infos = [info for info in self.root.value['itemCardInfoList']
		         if all(info.get(key) == value for key, value in criteria.items())]
		if not infos:
			return
		info, = infos
		return info

	@property
	def cost(self):
		return self._find_info(text="$val")["Value"]

	@property
	def weight(self):
		return self._find_info(text="$wt")["Value"]

	@property
	def favorite(self):
		"""Returns whether the item is favorited. Possible values are True, False, or None.
		None indicates the item is not favoritable."""
		if not self.root.value['canFavorite']:
			return
		return self.root.value['favorite'] >= 0

	@property
	def favorite_slot(self):
		"""If favorited, this indicates the numeric slot between 0 and 11 (left to right, then top to bottom).
		Otherwise None."""
		if not self.favorite:
			return
		return self.root.value['favorite']

	@property
	def equipped(self):
		"""Returned whether the item is equipped. Possible values are True, False or None.
		None indicates the item is not equippable."""
		state = self.root.value['equipState']
		if state is None:
			return None
		return state != 0

	@property
	def handle_id(self):
		return self.root.value['HandleID']

	@property
	def stack_id(self):
		return self.root.value['StackID']
