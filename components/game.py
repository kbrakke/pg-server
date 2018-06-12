'''
manages different components of the game
'''
from market import Market 
from board import Board 
from resources import Resources 
from auction import Auction
from phase import Phase
import random

class Game:
	'''
	determine player order
	auction power plants (in order)
	buy resources (reverse order!)
	build generators (reverse order!)
	bureaucracy
	'''

	def __init__(self):
		self.market = None
		self.players = []
		self.resources = None
		self.auction = Auction()  # since auction doesn't require any player settings, we can initialize it right away
		self.step = 1
		self.phase = Phase.DETERMINE_PLAYER_ORDER
		self.current_player = 0 	# which player's turn it is w.r.t the player_order index
		self.player_order = []

	def get_player_name(self, player_id):
		for player in self.players:
			if player.player_id == player_id:
				return player.name

	def player_can_afford(self, player_id, amount):
		for player in self.players:
			if player.player_id == player_id:
				return (player.money >= amount)

	def add_player(self, name, player_id):
		existing_names = [player.name for player in self.players]
		while name in existing_names:
			name = name + "!" # avoid duplicate names by adding exclamation marks
		player = Player(name, player_id)
		self.players.append(player)
		return name

	def start_game(self):
		'''
		kicks off the game
		'''
		settings = {'board_type': 'europe', 'num_players': len(self.players)}
		self.market = Market(settings)
		self.resources = Resources(settings)
		self.board = Board(settings)
		self.phase_one()

	def next_turn(self):
		'''
		advances the turn/phase
		'''
		if self.current_turn < (len(player_order) -1):
			# we are still in the same phase 
			self.current_player += 1 
		else:
			self.current_player = 0 
			if self.phase == Phase.AUCTION:
				self.player_order.reverse()
				self.phase = Phase.BUY_RESOURCES 
			elif self.phase == Phase.BUY_RESOURCES:
				self.phase == Phase.BUILD_GENERATORS 
			elif self.phase == Phase.BUILD_GENERATORS:
				self.phase = Phase.BUREAUCRACY 
				self.player_order.reverse()
				# wait to trigger phase_five() until all players have powered
				# self.phase_five()

	def resolve_turn(self):
		'''
		resolves the current turn due to lack of response from user
		'''
		self.next_turn()

	def phase_one(self):
		'''
		determine player order
		'''
		if self.player_order == []:
			# it's the first round! we randomly choose
			players = [player.player_id for player in self.players]
			random.shuffle(players)
			self.player_order = players 
		else:
			self.player_order = []
			not_yet_picked = [player.player_id for player in self.players]
			while len(self.player_order) != len(self.players):
				top = max(not_yet_picked, key=lambda x: self.board.num_cities(x))
				num_cities = self.board.num_cities(top)
				ties = [player for player in self.players if self.board.num_cities(player.player_id) == top]
				rank = sorted(ties, key=lambda x: x.highest_powerplant(), reverse=True)
				for player in rank:
					self.player_order.append(player.player_id)
					not_yet_picked.remove(player.player_id)
		self.phase = Phase.AUCTION

	def auction_pass(self, player_id):
		'''
		player_id passed on the current auction 
		'''
		if not self.auction.auction_in_progress:
			# the player is the leader! They can no longer bid
			for player in self.players:
				if player.player_id == player_id:
					player.can_bid = False
			self.next_turn()
		else:
			self.auction.can_bid.remove(player_id)
			if len(self.auction.can_bid) == 1:
				self.auction.auction_in_progress = False
				# someone has won the bid!
				winner = self.auction.can_bid[0]
				for player in self.players:
					if player.player_id == winner:
						player.can_bid = False 
						won_plant = self.market.buy(self.auction.currently_for_bid)
						player.powerplants.append(won_plant)
						player.money -= self.auction.current_bid
						logger.info("{} won the auction! Bought powerplant {} for {} money".format(player.player_name, self.auction.currently_for_bid, self.auction.current_bid))
						if self.auction.to_be_trashed is not None:
							logger.info("{} has too many plants! Trashing powerplant {}".format player.player_name, self.auction.to_be_trashed)
							player.trash_powerplant(self.auction.to_be_trashed)
						if player.player_id == self.player_order[self.current_player]:
							self.next_turn()
						break
			else:
				self.auction.advance_bid()


	def auction_bid(self, player_id, bid, powerplant, trash_id):
		'''
		player_id submitted 'bid' money for the current auction
		'''
		if self.auction.auction_in_progress:
			self.auction.current_bid = bid 
			self.auction.winning_bidder = player_id 
			self.auction.to_be_trashed = trash_id
			self.auction.advance_bid()
		else:
			biddable_players = [player.player_id for player in self.players if player.can_bid]
			if len(biddable_players) == 1:
				# special case; there is no auction
				for player in self.players:
					if player.player_id == player_id:
						player.can_bid = False 
						won_plant = self.market.buy(powerplant)
						player.powerplants.append(won_plant)
						player.money -= self.auction.current_bid
						logger.info("{} won the auction! Bought powerplant {} for {} money".format(player.player_name, powerplant, bid))
						if trash_id is not None:
							logger.info("{} has too many plants! Trashing powerplant {}".format player.player_name, self.auction.to_be_trashed)
							player.trash_powerplant(trash_id)
						self.next_turn()
						return
			else:
				self.auction.can_bid = [player_code for player_code in self.player_order if player_code in biddable_players]
				name = self.get_player_name(player_id)
				self.auction.current_bidder = 1
				logger.info("{} started an auction for powerplant {}".format(name, powerplant))
				self.auction.currently_for_bid = powerplant 
				self.auction.winning_bidder = player_id 
				self.auction.bid = bid 
				self.auction.to_be_trashed = trash_id
				self.auction.auction_in_progress = True


	def build_generator(self, player_id, path):
		'''
		build a generator in the designated city
		'''
		cost_to_build = self.board.player_purchase(player_id, path)
		for player in self.players:
			if player.player_id == player_id:
				player.money -= cost_to_build
				break
		num_owned_cities = self.board.num_cities(player_id)
		if num_owned_cities >= self.market.currently_available[0]["market_cost"]:
			self.market.trash_low_powerplants(num_owned_cities)

	def phase_five(self):
		'''
		bureaucracy
		'''
		self.phase = Phase.DETERMINE_PLAYER_ORDER
		self.phase_one()