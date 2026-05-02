import random

PROMOTIONS = {
    "\nFor a more modern UNO experience, <a href=\"https://t.me/uno9bot/uno\">try out</a> the new <a href=\"https://t.me/uno9bot?start=ref-unobot\">@uno9bot</a>.\n": 2.0,
    "\nAlso check out @UnoDemoBot, a newer version of this bot with exclusive modes and features!\n": 1.0,
}


def get_promotion():
    return random.choices(list(PROMOTIONS.keys()), weights=list(PROMOTIONS.values()))[0]


async def send_promotion(chat, chance=1.0):
    if random.random() <= chance:
        await chat.send_message(get_promotion(), parse_mode='HTML')
