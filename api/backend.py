from flask import Flask, request, redirect, url_for
import random

from card_scripting import cardPlayer, cards

app = Flask(__name__)
num_games = 0
games = []


class Game:
    def __init__(self):
        """Initializes game, for now this just assumes 1 player and a starting deck
        TODO: support for more than one player"""
        self.nextCardID = 0
        deck = ['village', 'village', 'village', 'village', 'village', 'copper', 'copper', 'copper', 'copper', 'copper']
        self.deck = [self.make_card(c) for c in deck]
        # self.supply = random.sample(sorted(cards.supply_options), 10)
        
        #to sort the cards by cost the self.supply needs to be sorted
        self.supply = ['market', 'festival', 'council_room', 'moat', 'militia', 'village', 'smithy', 'laboratory', 'witch', 'gardens']
        # change to [10 for i in range(10)] to make it take the right number of cards to finish the game=
        self.supplySizes = [2 for i in range(10)]
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
        global num_games
        self.id = num_games
        num_games += 1
        self.shuffle()
        self.draw_cards(5)

    def make_card(self, name):
        """returns a card object with the given name"""
        card = cards.getCard(name).copy()
        card['id'] = self.nextCardID
        card['name'] = name
        self.nextCardID += 1
        return card

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
        


@app.route("/cardbought/<int:game_id>/<card_name>/")
def card_bought(game_id, card_name):
    game = games[game_id]
    cost = cards.getCard(card_name)['cost']
    if game.coins >= cost and game.buys >= 1:
        card = game.make_card(card_name)
        game.discard.append(card)
        game.coins -= cost
        game.buys -= 1
        game.supplySizes[game.supply.index(card_name)] -= 1

        
    return "hi"  # nothing actually needs to be returned, flask crashes without this.

@app.route("/cardplayed/<int:game_id>/<int:card_id>/")
def card_played(game_id, card_id):
    game = games[game_id]
    hand = game.hand

    idx = game.find_card_in_list(hand, card_id)

    if idx == -1:
        raise ValueError
    
    card = game.hand[idx]
    type = card['type']
    if (type == 'action' and game.phase == 'action') or (type == 'treasure' and game.phase == 'buy'):
        if type == 'action':
            if game.actions >= 1:
                game.actions -= 1
            else:
                return "hi"
        game.in_play.append(card)
        game.hand.pop(idx)
        cmd = cardPlayer.getCardCmd(game_id, card['name'])
        game.cmd = cmd
        res = cmd.execute()
        if res == "yield":
            return {'yield': True}

    return {'yield': False}


@app.route("/gethand/<int:game_id>/")
def get_hand(game_id):
    return str(games[game_id].hand)

@app.route("/getgamestate/<int:game_id>/")
def getgamestate(game_id):
    state = {}
    state["hand"] = games[game_id].hand
    state["discard"] = games[game_id].discard
    state["in_play"] = games[game_id].in_play
    state["deck"] = games[game_id].deck
    state["phase"] = games[game_id].phase
    state["actions"] = games[game_id].actions
    state["buys"] = games[game_id].buys
    state["coins"] = games[game_id].coins
    state["supply"] = games[game_id].supply
    return state


@app.route("/getfrontstate/<int:game_id>/")
def getfrontstate(game_id):
    state = {}
    state["hand"] = games[game_id].hand
    state["discard"] = games[game_id].discard
    state["in_play"] = games[game_id].in_play
    state["phase"] = games[game_id].phase
    state["actions"] = games[game_id].actions
    state["buys"] = games[game_id].buys
    state["coins"] = games[game_id].coins
    state["supply"] = games[game_id].supply
    state["supplySizes"] = games[game_id].supplySizes
    return state

@app.route('/changeVar/', methods=['POST'])
def change_var():
    req = request.get_json()
    gameID = req['gameID']
    var = req['var']
    delta = int(req['delta'])
    if var == "actions":
        games[gameID].actions += delta
    elif var == "buys":
        games[gameID].buys += delta
    elif var == "coins":
        games[gameID].coins += delta
    else:
        raise ValueError("Invalid variable name")
    return 'Changed variable' # nothing actually needs to be returned, flask crashes without this.

@app.route('/changeZone/', methods=['POST'])
def change_zone():
    req = request.get_json()
    gameID = req['gameID']
    game = games[gameID]
    cards = req['cards']
    card_ids = [card['id'] for card in cards]
    zone = req['zone']

    dest = None
    if zone == 'discard':
        dest = game.discard
    elif zone == 'hand':
        dest = game.hand
    elif zone == 'deck':
        dest = game.deck
    elif zone == 'trash':
        dest = game.trash

    for card_id in card_ids:
        card_loc = game.find_card(card_id)
        if card_loc[1] == -1:
            continue
        dest.append(card_loc[0].pop(card_loc[1]))

    return 'Changed zone'



@app.route('/endphase/<int:game_id>/')
def end_phase(game_id):
    game = games[game_id]
    if game.phase == "action":
        game.phase = "buy"
    elif game.phase == "buy":
        game.end_turn()
    return "ended phase"

@app.route("/getsupply/<int:game_id>/")
def get_supply(game_id):
    game = games[game_id]
    return {"store": [game.make_card(game.supply[i]) for i in range(10) if game.supplySizes[i] > 0]}

@app.route("/draw/<int:game_id>/<int:num_cards>/")
def draw(game_id, num_cards):
    games[game_id].draw_cards(num_cards)
    return 'hello world' # nothing actually needs to be returned, flask crashes without this.

@app.route("/newgame/")
def new_game():
    games.append(Game())
    return str(num_games - 1)

@app.route("/selected/<int:game_id>/", methods=['POST'])
def selected(game_id):
    req = request.get_json()
    ids = req['ids']
    game = games[game_id]
    game.options = None
    cards = game.find_card_objs(ids)
    game.cmd.setPlayerInput(cards)
    res = game.cmd.execute()

    if res == "yield":
        return "yield"

    return "Hello World!"

@app.route("/setoptions/<int:game_id>/", methods=['POST'])
def set_options(game_id):
    req = request.get_json()
    games[game_id].options = req
    return "hello world" # nothing actually needs to be returned, flask crashes without this.

@app.route("/ischoice/<int:game_id>/")
def ischoice(game_id):
    return {'is_choice': games[game_id].options != None}
    
@app.route("/getoptions/<int:game_id>/")
def get_options(game_id):
    return games[game_id].options

@app.route("/findcards/<int:game_id>/")
def find_cards(game_id):
    return {'res': games[game_id].find_card_objs([1, 2, 3, 4])}

# Does not always work for some reason, I will look at it
@app.route("/calculatescore/<int:game_id>/")
def calculate_score(game_id):
    score = 0
    for c in games[game_id].deck:
        if(c['name'] == 'estate'):
            score += 1
        if(c['name'] == 'duchy'):
            score += 3
        if(c['name'] == 'province'):
            score += 6
        if(c['name'] == "gardens"):
            score += (len(games[game_id].deck)/10)
    return {'score' : score}


# @app.route("deckcomposition/<int:game_id>/")
# def deck_composition(game_id):
#     deck_comp = { : }
#     return deck_comp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    Game()
