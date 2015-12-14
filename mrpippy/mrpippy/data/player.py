

class Player(Data):
	"""Contains high level info or direct player-related data"""

	def from_manager(self, manager):
		return manager.root

	@property
	def locked(self):
		"""Indicates you shouldn't try to make changes right now"""
		status = self.value['Status']
		return any([
			status['IsInAutoVanity'],
			status['IsPlayerDead'],
			status['IsMenuOpen'],
			status['IsInVatsPlayback'],
			status['IsPlayerPipboyLocked'],
			status['IsPlayerMovementLocked'],
			status['IsPipboyNotEquipped'],
			status['IsLoading'],
		])

	@property
	def location(self):
		map = self.value['Map']
		# CurrCell is empty when outdoors?
		return map['CurrCell'] or map['CurrWorldSpace']

	@property
	def coordinates(self):
		"""World coords of player"""
		player = self.value['Map']['World']['Player']
		return player['X'], player['Y']

	@property
	def limbs(self):
		"""Returns a dict {body part: condition between 0 and 1}"""
		parts = {"Head", "RLeg", "RArm", "LLeg", "LArm", "Torso"}
		stats = self.value['Stats']
		return {part: stats["{}Condition".format(part)] / 100.0 for part in parts}

	@property
	def name(self):
		return self.value['PlayerInfo']['name']

	@property
	def hp(self):
		return self.value['PlayerInfo']['CurrHP']

	def hp_with_healing(self):
		"""Currently projected total HP after all healing effects apply."""
		return min(self.maxhp, self.hp + self.value['PlayerInfo']['CurrentHPGain']

	@property
	def maxhp(self):
		return self.value['PlayerInfo']['MaxHP']

	@property
	def level(self):
		"""Note this is a float and includes progress to next level"""
		playerinfo = self.value['PlayerInfo']
		return playerinfo['XPLevel'] + playerinfo['XPProgressPct']

	@property
	def weight(self):
		return self.value['PlayerInfo']['CurrWeight']

	@property
	def maxweight(self):
		return self.value['PlayerInfo']['MaxWeight']

	@property
	def name(self):
		return self.value['PlayerInfo']['name']

	@property
	def hour(self):
		return self.value['PlayerInfo']['TimeHour']

	@property
	def time(self):
		"""Returns the in-game time in unix epoch time.
		Let's hope they solved the 2038 problem!"""
		playerinfo = self.value['PlayerInfo']
		return timegm((
			2000 + playerinfo['DateYear'],
			playerinfo['DateMonth'],
			playerinfo['DateDay'],
			0, 0, 0 # hour, min, sec
		)) + playerinfo['TimeHour'] * 3600

	@property
	def perks(self):
		"""Returns a dict {perk name: rank} of (non-hidden) perks the player has (ie. all ranks are at least 1)"""
		return {
			perk['Name']: perk['Rank']
			for perk in self.value['Perks']
			if perk['Name'] and perk['Rank']

	@property
	def radio(self):
		"""Currently active radio station. Returns string name, or None."""
		active = [radio['text'] for radio in self.value['Radio'] if radio['active']]
		if not active:
			return
		active, = active
		return active

	@property
	def available_radios(self):
		"""Returns list of available radio stations by name."""
		return [radio['text'] for radio in self.value['Radio'] if radio['inRange']]

	@property
	def special(self):
		"""Returns a tuple of player's S.P.E.C.I.A.L. stats, in order."""
		return [stat['Value'] + stat['Modifier'] for stat in self.value['Special']]

	@property
	def base_special(self):
		"""As special, but without temporary modifiers."""
		return [stat['Value'] for stat in self.value['Special']]
