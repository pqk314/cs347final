from card_scripting import cardParser
from card_scripting import cards

def playCard(gameID, card): 
    text = cards.getCardText(card)
    cmd = cardParser.multicommand(text, gameID)
    cmd.execute()