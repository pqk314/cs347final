import requests


def take_turn(player):
    """AI takes a turn"""
    requests.get(f"http://localhost:5000/endphase/{player.game.id}/{player.id}/")
    to_play = []
    for card in player.hand:
        if card['type'] == 'treasure':
            to_play.append(card['id'])
    while to_play:
        requests.get(f"http://localhost:5000/cardplayed/{player.game.id}/{player.id}/{to_play.pop()}/")
    if player.coins >= 8 and player.game.supplySizes['province'] > 0:
        requests.get(f"http://localhost:5000/cardbought/{player.game.id}/{player.id}/province/")
    elif player.coins >= 6 and player.game.supplySizes['province'] > 4 and player.game.supplySizes['gold'] > 0:
        requests.get(f"http://localhost:5000/cardbought/{player.game.id}/{player.id}/gold/")
    elif player.coins >= 5 and player.game.supplySizes['province'] <= 4 and player.game.supplySizes['duchy'] > 0:
        requests.get(f"http://localhost:5000/cardbought/{player.game.id}/{player.id}/duchy/")
    elif player.coins >= 3 and player.game.supplySizes['province'] > 4 and player.game.supplySizes['silver'] > 0:
        requests.get(f"http://localhost:5000/cardbought/{player.game.id}/{player.id}/silver/")
    elif player.coins >= 2 and player.game.supplySizes['province'] <= 4 and player.game.supplySizes['estate'] > 0:
        requests.get(f"http://localhost:5000/cardbought/{player.game.id}/{player.id}/estate/")
    if player.coins >= 6 and player.buys == 1:
        requests.get(f"http://localhost:5000/cardbought/{player.game.id}/{player.id}/gold/")
    elif player.coins >= 3 and player.buys == 1:
        requests.get(f"http://localhost:5000/cardbought/{player.game.id}/{player.id}/silver/")
    requests.get(f"http://localhost:5000/endphase/{player.game.id}/{player.id}/")


def make_selection(options, max_num, can_choose_less):
    """AI makes a selection"""
    if can_choose_less:
        return []
    priority = ['curse', 'estate', 'duchy', 'province', 'copper', 'silver', 'gold']
    selected = []
    for name in priority:
        for card in options:
            if card['name'] == name:
                selected.append(card)
            if len(selected) >= max_num:
                break
    while len(selected) > max_num:
        selected.pop()
    return selected
