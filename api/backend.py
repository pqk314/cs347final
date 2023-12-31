from flask import Flask, request
from game import Game
import psycopg2
from card_scripting import cards
import aiplayer

app = Flask(__name__)

num_games = 0
games = []



DB_NAME = "docker"
DB_USER = "docker"
DB_PASS = "docker"
DB_HOST = "db"
DB_PORT = "5432"

def find_card_in_list(list, card_id):
    """This is used to figure out if a card is in a list, like if a card is in your hand."""
    for idx, card in enumerate(list):
        if card['id'] == card_id:
            return idx
    return -1

@app.route("/cardbought/<int:game_id>/<int:player_id>/<card_name>/")
def card_bought(game_id, player_id, card_name):
    """Makes sure it is your turn and the game is still happening. Also checks whether you have the money to buy
    what the backend was told."""
    if game_over(game_id)['game_over']:
        return 'game_ended'
    game = games[game_id]
    player = game.currentPlayer
    if player_id != player.id or player.barrier != '' or player.options is not None:
        return "Nice try"
    cost = cards.getCard(card_name)['cost']
    if player.coins >= cost and player.buys >= 1 and player.phase == 'buy' and game.supplySizes[card_name] > 0:
        card = game.make_card(card_name)
        player.discard.append(card)
        for p in game.players:
            p.updates['size_update'] = p.deck_info()
        player.coins -= cost
        game.update_all_players('set_coins', player.coins)
        player.buys -= 1
        game.update_all_players('set_buys', player.buys)
        game.supplySizes[card_name] -= 1
        for player in game.players:
            if player != game.currentPlayer:
                player.set_text(f"Player {game.get_player_number(player_id)} bought a {(' '.join(card_name.split('_')).title())}.")
            else:
                player.set_text("Left click a card to play it.")

        
    return "hi"  # nothing actually needs to be returned, flask crashes without this.

@app.route("/cardplayed/<int:game_id>/<int:player_id>/<int:card_id>/")
def card_played(game_id, card_id, player_id):
    """Lets player play cards if it is their turn and the game is still going"""
    if game_over(game_id)['game_over']:
        return 'game_ended'
    game = games[game_id]
    player = game.currentPlayer
    if player_id != player.id or player.barrier != '' or player.options is not None:
        return "can't play cards right now"
    hand = player.hand

    idx = find_card_in_list(hand, card_id)

    if idx == -1:
        raise ValueError
    
    card = player.hand[idx]
    type = card['type']
    if (type == 'action' and player.phase == 'action') or (type == 'treasure' and player.phase == 'buy'):
        if type == 'action':
            if player.actions >= 1:
                player.actions -= 1
                game.update_all_players('set_actions', player.actions)
            else:
                return "hi"
        player.in_play.append(card)
        if card['name'] == 'silver':
            player.coins += player.played_merchants
            player.played_merchants = 0
        removed_card = player.hand.pop(idx)
        player.update_list('remove', removed_card)
        for p in game.players:
            p.updates['size_update'] = p.deck_info()
        game.update_list_all_players('play', card['name'])
        player.set_command(cards.getCardText(card['name']))
        res = player.execute_command()
        if res == "yield":
            player.updates['select'] = True
            return {'yield': True}

    return {'yield': False}

@app.route("/getfrontstate/<int:game_id>/<int:playerid>/")
def getfrontstate(game_id, playerid):
    """Contains all information the front-end needs at a given time"""
    game = games[game_id]
    player = game.players[game.get_player_number(playerid) - 1]
    currentPlayer = game.currentPlayer
    state = {"hand": player.hand, "in_play": currentPlayer.in_play, "phase": currentPlayer.phase,
             "actions": currentPlayer.actions, "buys": currentPlayer.buys, "coins": currentPlayer.coins,
             "supply": game.supply, "supplySizes": game.supplySizes, "deckSize": len(currentPlayer.deck),
             "barrier": player.barrier, "text": player.text, 'deck_info': player.deck_info(),
             'player_num': game.get_player_number(playerid)}
    return state

@app.route('/endphase/<int:game_id>/<int:player_id>/')
def endphase(game_id, player_id):
    """Sequence for ending a phase whether it is the action or buy phase."""
    if not game_exists(game_id)['exists']:
        return "hi"
    game = games[game_id]
    player = game.currentPlayer
    if player_id != player.id or player.barrier != '' or player.options is not None:
        return "Nice try"

    if player.phase == "action":
        player.phase = "buy"
        game.update_all_players('set_phase', 'buy')
    elif player.phase == "buy":
        player.end_turn()
        if check_game_over(game):
            return 'game over'
        game.currentPlayer = game.players[game.get_player_number(player.id) % len(game.players)]
        game.update_all_players('set_phase', 'action')
        game.update_all_players('set_actions', 1)
        game.update_all_players('set_buys', 1)
        game.update_all_players('set_coins', 0)
        for player in game.players:
            player.set_barrier(f'It is Player {game.get_player_number(game.currentPlayer.id)}\'s turn.')
        game.currentPlayer.set_barrier('')
        game.update_all_players('new_turn', True)
        game.first_turn_ended = True
        if game.is_computer_game and game.currentPlayer == game.players[1]:
            aiplayer.take_turn(game.currentPlayer)
    return "ended phase"

def check_game_over(game):
    """only called at end of turn and can end game"""
    if game.is_over:
        return True
    empty_piles = 0
    for val in game.supplySizes.values():
        if val == 0:
            empty_piles += 1
    if empty_piles >= 3 or game.supplySizes['province'] == 0:
        game.is_over = True
        return True
    return False

@app.route("/newgame/")
def new_game():
    """makes a nenw game object"""
    global num_games
    global games
    games.append(Game(num_games, 2))
    num_games += 1
    game = games[-1]
    game.players[0].updates['new_game_prompt'] = True
    return {
        'game_id': str(game.id),
        'player_id': game.players[0].id
            }

@app.route('/joingame/<int:game_id>/')
def join_game(game_id):
    """Returns player id so a second player can join."""
    game = games[game_id]
    if game.first_turn_ended or not game.is_computer_game:
        return 'no lol'
    game.is_computer_game = False
    return str(game.players[1].id)

@app.route("/selected/<int:game_id>/", methods=['POST'])
def selected(game_id):
    """Checks whether player selection is legal."""
    req = request.get_json()
    ids = req['ids']
    game = games[game_id]
    if 'playerNum' in req:
        player = game.players[req['playerNum'] - 1]
    else:
        player = game.currentPlayer
    player.options = None
    cards = game.find_card_objs(ids)
    player.cmd.setPlayerInput(cards)
    res = player.execute_command()
    if res == "yield":
        return "yield"

    return "Hello World!"

@app.route("/<int:game_id>/<int:player_id>/okclicked/")
def reset_text(game_id, player_id):
    """Resets text if player clicks the OK button."""
    games[game_id].players[games[game_id].get_player_number(player_id) - 1].set_text('Left click a card to play it.')
    return 'text reset'
    
@app.route("/getoptions/<int:game_id>/<int:player_id>/")
def get_options(game_id, player_id):
    """Gets the options for the select menu"""
    game = games[game_id]
    player_options = game.players[game.get_player_number(player_id) - 1].options
    return player_options if player_options is not None else {}


@app.route("/updates/<int:game_id>/<int:player_id>")
def updates(game_id, player_id):
    """Gets player's updates for the front end"""
    if not game_exists(game_id)['exists']:
        return {'home_page': True}
    game = games[game_id]
    if game.is_over:
        return {'game_over': True}
    update_list = game.players[game.get_player_number(player_id) - 1].updates
    game.players[game.get_player_number(player_id) - 1].updates = {}
    return update_list

def calculate_score(game_id):
    game = games[game_id]
    scores = []
    for i in range(len(game.players)):
        player = game.players[i]
        scores.append(player.calculate_score())
    return scores

def deck_composition(deck):
    """Returns a dictionary of how frequent each card (f.e. {'silver': 10}"""
    deck_comp = {}
    for card in deck:
        if card == 'fake':
            continue
        if card in deck_comp:
            deck_comp[card] += 1
        else:
            deck_comp[card] = 1
    return deck_comp

@app.route("/gameexists/<int:game_id>/")
def game_exists(game_id):
    return {'exists': num_games > game_id}

@app.route('/gameisover/<int:game_id>/')
def game_over(game_id):
    """different from check_game_over because this can't end the game."""
    return {'game_over': games[game_id].is_over}

@app.route("/createtable/")
def createtable():
    """Creates SQL table. Restarts docker container if SQL hasn't initialized yet."""
    try:
        conn = psycopg2.connect(database=DB_NAME,
                            user=DB_USER,
                            password=DB_PASS,
                            host=DB_HOST,
                            port=DB_PORT)

        cur = conn.cursor()  # creating a cursor
 
        # executing queries to create table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Games
        (
            ID BIGINT   PRIMARY KEY NOT NULL,
            DECK TEXT[][],
            VP BIGINT[]
        )
        """)
        
        # commit the changes
        conn.commit()
        conn.close()
        print("Table Created successfully")

    except:
        raise ConnectionError('PostgresSQL rejected connection. Trying again')
    return "hi"


@app.route("/save/<int:game_id>/")
def save(game_id):
    """Saves a game's info in DB"""
    game = games[game_id]
    if game.db_id != -1:
        return str(game.db_id)
    decks = []
    for player in game.players:
        decks.append(sorted(player.deck + player.discard + player.hand + player.in_play, key=lambda card: card['name']))

    hand_lists = "{"
    for deck in decks:
        savehand = "{"
        for i in range(len(max(decks, key=len))):
            if i < len(deck):
                savehand += f"{deck[i]['name']},"
            else:
                savehand += 'fake,'
        savehand = savehand[:-1]
        savehand += "}"
        hand_lists += savehand + ","
    hand_lists = hand_lists[:-1]
    hand_lists += "}"


    conn = psycopg2.connect(database=DB_NAME,
                            user=DB_USER,
                            password=DB_PASS,
                            host=DB_HOST,
                            port=DB_PORT)
    cur = conn.cursor()
    id = get_num_games()
    vps = f'{{{str(calculate_score(game_id))[1:-1]}}}'
    cur.execute("INSERT INTO Games (ID,DECK,VP) VALUES (% s,'% s', '%s')" % (id, hand_lists, vps))
    conn.commit()
    conn.close()
    game.db_id = id
    return str(id)

# returns a list that conatins all of the cards in the first player's hand
@app.route("/dbget/<int:game_id>/")
def dbget(game_id):
    """Fetches DB info for game_id"""
    returnjson = {'deck':""}
    # getting the people back
    conn = psycopg2.connect(database=DB_NAME,
                        user=DB_USER,
                        password=DB_PASS,
                        host=DB_HOST,
                        port=DB_PORT)
    cur = conn.cursor()
    cur.execute("SELECT DECK, VP FROM Games WHERE ID=%s", (game_id,))
    rows = cur.fetchall()
    game = rows[0]
    # game should be of the form (0, ['copper', 'cellar', 'copper', 'copper', 'copper']) 
    # handlist is a list

    conn.close()
    # due to multihands
    returnjson['deck'] = game
    return returnjson


# This is the endpoint we need completed
# This returns a [game1, game2, game3] where gamex = [play1hand, player2hand, player3hand] where playerxhand = ['copper', 'cellar']
@app.route("/getstats/")
def getstats():
    """Gets info form all games for method made by Backgammon team."""
    ans = []

    conn = psycopg2.connect(database=DB_NAME,
                        user=DB_USER,
                        password=DB_PASS,
                        host=DB_HOST,
                        port=DB_PORT)
    cur = conn.cursor()
    cur.execute("SELECT * FROM Games")
    rows = cur.fetchall()

    # like a list of game = rows[game_id]
    for r in rows:
        ans.append(r[1])

    conn.close()
    rtn = {'deck': ans}
    return rtn

def get_num_games():
    """Returns number of games stored in DB"""
    conn = psycopg2.connect(database=DB_NAME,
                            user=DB_USER,
                            password=DB_PASS,
                            host=DB_HOST,
                            port=DB_PORT)
    cur = conn.cursor()
    cur.execute("SELECT count(ID) FROM Games")
    ret = cur.fetchone()[0]
    conn.close()
    return ret

# return decks = {i:{estate:1}} where i is player num and {} is their deck comp
@app.route("/getgame/<int:game_id>")
def getgame(game_id):
    """Gets game info on specified ID"""
    ans = {}
    deck_comps = []
    table = dbget(game_id)['deck']
    hands = table[0]
    print(hands)
    vps = table[1]

    for deck in hands:
        deck_comps.append(deck_composition(deck))

        ans['deck_comps'] = deck_comps
        ans['score'] = vps
        
    return ans

@app.route('/getgames/')
def get_games():
    """Returns a dictionary containing all games stored in the database to support the game browser"""
    ret = {}
    conn = psycopg2.connect(database=DB_NAME,
                            user=DB_USER,
                            password=DB_PASS,
                            host=DB_HOST,
                            port=DB_PORT)
    cur = conn.cursor()
    cur.execute("SELECT ID,VP FROM Games")
    for game in cur:
        ret[len(ret)] = {'id': game[0], 'vp': game[1]}
    conn.close()
    return ret

if __name__ == "__main__":
    createtable()
    
    app.run(host="0.0.0.0", port=5000)
