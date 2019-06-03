from datetime import datetime
from os import getenv

from dotenv import load_dotenv
from myfitnesspal import Client

load_dotenv('../../secret_files/.env')

USERNAME = getenv('EMAIL')
PASSWORD = getenv('MFP_PASSWORD')

NOW = datetime.now()


def get_calories_consumed(t):
    from pprint import pprint

    pprint(t)
    return t.totals['calories']


def get_carbohydrates(t):
    return t.totals['carbohydrates']


def get_fat(t):
    return t.totals['fat']


def get_protein(t):
    return t.totals['protein']


def get_sodium(t):
    return t.totals['sodium']


def get_sugar(t):
    return t.totals['sugar']


if __name__ == '__main__':
    _c = Client(USERNAME, PASSWORD)
    _t = _c.get_date(NOW.year, NOW.month, NOW.day)

    print(f'Calories Consumed: {get_calories_consumed(_t)}')
    print(f'Carbohydrates Consumed: {get_carbohydrates(_t)}')
    print(f'Fat Consumed: {get_fat(_t)}')
    print(f'Protein Consumed: {get_protein(_t)}')
    print(f'Sodium Consumed: {get_sodium(_t)}')
    print(f'Sugar Consumed: {get_sugar(_t)}')
