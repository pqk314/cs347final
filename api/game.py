from card_scripting import cards
from player import player
import random

class Game:
    def __init__(self, id, num_players):
        # Initializes game
        self.basesupply = ['copper', 'silver', 'gold', 'estate', 'duchy', 'province', 'curse']
        self.supply = random.sample(cards.supply_options, 10)
        self.supply.sort(key=lambda card: cards.getCard(card)['cost'])
        self.supplySizes = {key: 10 for key in self.supply}
        self.supplySizes['copper'] = 60 - 7*num_players
        self.supplySizes['silver'] = 40
        self.supplySizes['gold'] = 30
        victorySizes = 12 if num_players > 2 else 8
        self.supplySizes['estate'] = victorySizes
        self.supplySizes['duchy'] = victorySizes
        self.supplySizes['province'] = victorySizes
        self.floatingCards = []
        self.trash = []
        if 'gardens' in self.supply:
            self.supplySizes['gardens'] = victorySizes
        self.supplySizes['curse'] = 10*num_players - 10
        self.nextCardID = 0
        self.gamestateID = 0
        deck_cards = ['copper', 'copper', 'copper', 'copper', 'copper', 'copper', 'copper', 'estate', 'estate', 'estate']
        self.players = []
        for i in range(num_players):
            deck = [self.make_card(c) for c in deck_cards]
            newPlayer = player(self, deck, self.make_player_id())
            if i > 0:
                newPlayer.set_barrier("It is Player 1's turn.")
            self.players.append(newPlayer)
        self.currentPlayer = self.players[0]

        self.is_computer_game = True
        self.first_turn_ended = False
        self.is_over = False
        self.db_id = -1

        self.id = id

    def make_player_id(self):
        """Gets a new unique player ID"""
        id = random.randint(0, 1000000000)
        new_id = id
        while True:
            for player in self.players:
                if player.id == id:
                    id = random.randint(0, 1000000000)
            if id == new_id:
                break
            else:
                new_id = id
        return id


    def get_player_number(self, player_id):
        """Takes in player ID and outputs number that is that players location in the players array"""
        for i in range(len(self.players)):
            if self.players[i].id == player_id:
                return i + 1
        raise ValueError('Player ID not found')

    def update_all_players(self, key, val):
        """Gives all players update at (key,val)"""
        for p in self.players:
            p.updates[key] = val

    def update_list_all_players(self, key, val):
        """Gives all players update at (key,val) in list format"""
        for p in self.players:
            p.update_list(key, val)

    def make_card(self, name):
        """returns a card object with the given name"""
        card = cards.getCard(name).copy()
        card['id'] = self.nextCardID
        card['name'] = name
        self.nextCardID += 1
        return card

    def find_card_in_list(self, list, card_id):
        """Finds card index in the list"""
        for idx, card in enumerate(list):
            if card['id'] == card_id:
                return idx
        return -1

    def find_card(self, card_id):
        """Searches everywhere for cards"""
        idx = self.find_card_in_list(self.floatingCards, card_id)
        if idx != -1:
            return self.floatingCards, idx
        for player in self.players:
            l, idx = player.find_card(card_id)
            if idx != -1:
                return l, idx
        return [], -1
    
    def find_card_objs(self, card_ids):
        """Calls find_card on each card_id in card_ids"""
        objs = []
        for card_id in card_ids:
            l, idx = self.find_card(card_id)
            if idx!= -1:
                objs.append(l[idx])
        return objs
