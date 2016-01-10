
from calendar import timegm

from common import Data


class Player(Data):
	"""Contains high level info or direct player-related data"""

	def from_manager(self, manager):
		return manager.root

	@property
	def locked(self):
		"""Indicates you shouldn't try to make changes right now"""
		return self.status is not None

	@property
	def status(self):
		"""Returns a string describing the player's current state (dead, in vats, etc),
		or None if player is in no special state."""
		# list of (key, description) in priority order
		flags = [
			("IsDataUnavailable", "data unavailable"),
			("IsPlayerDead", "dead"),
			("IsLoading", "loading"),
			("IsInAutoVanity", "in auto vanity"),
			("IsMenuOpen", "in menu"),
			("IsPipboyNotEquipped", "no pipboy"),
			("IsPlayerPipboyLocked", "pipboy locked"),
			("IsPlayerMovementLocked", "movement locked"),
			("IsInVats", "in vats"),
			("IsInVatsPlayback", "in vats playback"),
			("IsPlayerInDialogue", "in dialogue"),
			("IsInAnimation", "in animation"),
		]
		status = self.root['Status']
		for key, description in flags:
			if status[key].value:
				return description

	@property
	def location(self):
		map = self.root['Map']
		# CurrCell is empty when outdoors?
		return map['CurrCell'].value or map['CurrWorldspace'].value

	@property
	def coordinates(self):
		"""World coords of player"""
		player = self.root['Map']['World']['Player']
		return player['X'].value, player['Y'].value

	@property
	def limbs(self):
		"""Returns a dict {body part: condition between 0 and 1}"""
		parts = {"Head", "RLeg", "RArm", "LLeg", "LArm", "Torso"}
		stats = self.root['Stats']
		return {part: stats["{}Condition".format(part)].value / 100.0 for part in parts}

	@property
	def name(self):
		return self.root['PlayerInfo']['PlayerName'].value

	@property
	def hp(self):
		return self.root['PlayerInfo']['CurrHP'].value

	@property
	def maxhp(self):
		return self.root['PlayerInfo']['MaxHP'].value

	@property
	def level(self):
		"""Note this is a float and includes progress to next level"""
		playerinfo = self.root['PlayerInfo']
		return playerinfo['XPLevel'].value + playerinfo['XPProgressPct'].value

	@property
	def weight(self):
		return self.root['PlayerInfo']['CurrWeight'].value

	@property
	def maxweight(self):
		return self.root['PlayerInfo']['MaxWeight'].value

	@property
	def hour(self):
		return self.root['PlayerInfo']['TimeHour'].value

	@property
	def time(self):
		"""Returns the in-game time in unix epoch time.
		Let's hope they solved the 2038 problem!"""
		playerinfo = self.root['PlayerInfo']
		return timegm((
			2000 + playerinfo['DateYear'].value,
			playerinfo['DateMonth'].value,
			playerinfo['DateDay'].value,
			0, 0, 0 # hour, min, sec
		)) + playerinfo['TimeHour'].value * 3600

	@property
	def perks(self):
		"""Returns a dict {perk name: rank} of (non-hidden) perks the player has (ie. all ranks are at least 1)"""
		return {
			perk['Name']: perk['Rank']
			for perk in self.root['Perks'].value
			if perk['Name'] and perk['Rank']
		}

	@property
	def radio(self):
		"""Currently active radio station. Returns string name, or None."""
		active = [radio['text'] for radio in self.root['Radio'].value if radio['active']]
		if not active:
			return
		active, = active
		return active

	@property
	def available_radios(self):
		"""Returns list of available radio stations by name."""
		return [radio['text'] for radio in self.root['Radio'].value if radio['inRange']]

	@property
	def special(self):
		"""Returns a tuple of player's S.P.E.C.I.A.L. stats, in order."""
		return [stat['Value'] for stat in self.root['Special'].value]

	@property
	def base_special(self):
		"""As special, but without temporary modifiers."""
		return [stat['Value'] - stat['Modifier'] for stat in self.root['Special'].value]
