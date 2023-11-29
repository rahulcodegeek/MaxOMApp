from database import restaurants_bot


def get_bot(number):
    bot = restaurants_bot.query.filter_by(restuarant_number=number).first()
    return bot
