from flask import Flask, request, redirect, url_for, render_template
import random
import requests

from card_scripting import cardPlayer, cards


class player:
    def __init__(self, game, deck, id):
        self.game = game
        """Initializes a player, for now this just assumes 1 player and a starting deck"""
        self.deck = deck
        self.id = id
        # self.supply = random.sample(sorted(cards.supply_options), 10)
        
        self.hand = []
        self.discard = []
        self.in_play = []
        self.trash = []
        self.phase = "action"
        self.actions = 1
        self.buys = 1
        self.coins = 0
        self.cmd = None
        self.options = None
        self.shuffle()
        self.draw_cards(5)


    def draw_cards(self, num_to_draw):
        """draws cards while attempting to catch edge cases. I may have forgotten one, but this may be final."""
        for i in range(num_to_draw):
            if len(self.deck) == 0 and len(self.discard) == 0:
                break
            if len(self.deck) == 0:
                self.deck = self.discard
                self.discard = []
                self.shuffle()
            self.hand.append(self.deck.pop())

    def find_card_in_list(self, list, card_id):
        for idx, card in enumerate(list):
            if card['id'] == card_id:
                return idx
        return -1

    def find_card(self, card_id):
        for l in [self.hand, self.deck, self.discard, self.in_play, self.trash]:
            idx = self.find_card_in_list(l, card_id)
            if idx != -1:
                return l, idx
        return [], -1
    
    def find_card_objs(self, card_ids):
        objs = []
        for card_id in card_ids:
            l, idx = self.find_card(card_id)
            if idx!= -1:
                objs.append(l[idx])
        return objs

    def shuffle(self):
        """shuffles deck"""
        random.shuffle(self.deck)

    def end_turn(self):
        """Discards all cards in hand and in front of player"""
        while len(self.hand) > 0:
            self.discard.append(self.hand.pop())
        while len(self.in_play) > 0:
            self.discard.append(self.in_play.pop())
        self.draw_cards(5)
        self.actions = 1
        self.buys = 1
        self.coins = 0
        self.phase = 'action'


    def get_deck_composition(self):
        cards = self.deck + self.hand + self.in_play + self.discard
        deck_comp = {}
        for card in cards:
            if card['name'] in deck_comp:
                deck_comp[card['name']] += 1
            else:
                deck_comp[card['name']] = 1
        return deck_comp
    
    def calculate_score(self):
        score = 0
        cards = self.deck + self.hand + self.in_play + self.discard
        for c in cards:
            if(c['name'] == 'estate'):
                score += 1
            if(c['name'] == 'duchy'):
                score += 3
            if(c['name'] == 'province'):
                score += 6
            if(c['name'] == "gardens"):
                score += (len(cards)//10)
        return score