
from collections import defaultdict

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

	# maps from ammo type as per item info card to the name of the ammo item
	# All lower-case as different sources often cite different capitalization.
	# NOTE: for simplicity, we don't include the Syringer Ammo in this list (as it has variants)
	AMMO_TYPES = {
		'flare': 'flare',
		'.44': '.44 round',
		'10mm': '10mm round',
		'.308': '.308 round',
		'.38': '.38 round',
		'.45': '.45 round',
		'5.56mm': '5.56mm round',
		'railway spike': 'railway spike',
		'shell': 'shotgun shell',
		'mini nuke': 'mini nuke',
		'flamer': 'flamer fuel', # confirm?
		'5mm': '5mm round',
		'missile': 'missile',
		'cannonball': 'cannonball',
		'cell': 'fusion cell',
		'core': 'fusion core', # confirm?
		'plasma': 'plasma cartridge',
		'gamma': 'gamma round',
		'2mm ec': '2mm electromagnetic cartridge',
		'alien blaster': 'alien blaster round', # confirm?
		'cryo': 'cryo cell', # confirm?
	}

	# All grenade and mine-type weapon names.
	# All lower-case as different sources often cite different capitalization.
	GRENADE_NAMES = {
		'baseball grenade',
		'cryo grenade',
		'fragmentation grenade',
		'hallucigen gas grenade',
		'homing beacon',
		'institute beacon',
		'institute em pulse grenade',
		'molotov cocktail',
		'nuka grenade',
		'plasma grenade',
		'pulse grenade',
		'bottlecap mine',
		'cryo mine',
		'fragmentation mine',
		'nuke mine',
		'plasma mine',
		'pulse mine',
		'artillery smoke grenade',
		'synth relay grenade',
		'vertibird signal grenade',
	}

	# All alcohol-type aid item names.
	# All lower-case as different sources often cite different capitalization.
	ALCOHOL_NAMES = {
		# TODO
	}

	def __repr__(self):
		return "<{cls.__name__} {self.count}x {self.name!r}>".format(self=self, cls=type(self))
	__str__ = __repr__

	@property
	def inventory(self):
		return Inventory(self.manager)

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

	@property
	def effects(self):
		"""Returns a dict {effect name: value}, where name is something like 'Rads', 'HP'
		Note this is based off the displayed value in the pip boy, eg. something that gives
		+5 HP for 5 seconds will have value {'HP': 25}.
		We ignore any values that are intended to be interpreted as a percentage for simplicity.
		We ignore hidden values like '$wt' and '$val'.
		We ignore long description items.
		"""
		results = defaultdict(lambda: 0)
		for info in self.root.value['itemCardInfoList']:
			if info.get('showAsPercent'):
				continue
			if info.text.startswith('$'):
				continue
			if info.get('showAsDescription'):
				continue
			value = info['Value']
			if info.get('scaleWithDuration'):
				value *= info['duration']
			results[info['text']] += value

	@property
	def effects_text(self):
		"""Similar to effects, but instead of attempting to build a collection of true values,
		it attempts to collate strings for display of what the item does. It returns a list of strings
		such as "STR +1" or "HP +33%" or "Slows time for 10 seconds"
		"""
		results = []
		long_results = [] # long descriptions always go last
		for info in self.root.value['itemCardInfoList']:
			if info['text'].startswith('$'):
				continue
			if info.get('showAsDescription'):
				if info['text'] != 'HP':
					# work around for "cures all addictions" items,
					# which have 12 blank 'HP' entries with description True for some reason
					long_results.append(info['text'])
				continue
			value = info['Value']
			if info.get('scaleWithDuration'):
				value *= info['duration']
			value = '{:+.0f}'.format(value)
			if info.get('showAsPercent'):
				value += '%'
			results.append("{} {}".format(info['text'], value))
		return results + long_results

	@property
	def ammo_type(self):
		"""The name of the ammunition type for this item, if any.
		For items like firearms, returns the type as per the item card, eg. '.308'
		For items like grenades, returns the name of this item.
		If the item doesn't use ammo, returns None.
		"""
		if self.name.lower() in self.GRENADE_NAMES:
			return self.name
		for info in self.root.value['itemCardInfoList']:
			if info['text'].lower() in self.AMMO_TYPES:
				return info['text']

	@property
	def ammo(self):
		"""Returns the item that is ammunition for this item, if any.
		For items like firearms, returns the item for the ammo type used by the weapon.
		For items like grenades, simply returns self.
		If you are not carrying any of the ammo type, or if the item doesn't use ammo, returns None.
		"""
		ammo_type = self.ammo_type
		if not ammo_type:
			return
		if ammo_type == self.name:
			return self
		ammo_type = ammo_type.lower()
		for ammo_item in self.inventory.ammo:
			if ammo_item.name.lower() == self.AMMO_TYPES[ammo_type]:
				return ammo_item
