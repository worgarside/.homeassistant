from requests import get, ReadTimeout
from bs4 import BeautifulSoup
from datetime import datetime
from math import ceil
from time import sleep
from re import sub

DATA_LIMIT = 200.00


def get_remaining_data():
    from requests import get
    from re import sub
    from bs4 import BeautifulSoup
    from time import sleep

    while True:
        try:
            res = get('http://add-on.ee.co.uk/mbbstatus')

            soup = BeautifulSoup(res.content, 'html.parser')
            for small in soup('small'):
                small.decompose()

            allowance__left = soup.body.find('span', attrs={'class': 'allowance__left'}).text
            usage = float(
                sub(r"[\n\t\sA-Za-z]*", "", allowance__left)
            )

            if 'gb' not in allowance__left.lower() and 'mb' in allowance__left.lower():
                usage = usage / 1024
            else:
                raise ValueError(f'Unknown allowance__left element: {allowance__left}')

            return round(usage, 2)
        except AttributeError:
            sleep(1)
            continue


def get_allowance():
    while True:
        try:
            res = get('http://add-on.ee.co.uk/mbbstatus')
            soup = BeautifulSoup(res.content, 'html.parser')
            days_remaining, hours_remaining = [int(b.text) for b in
                                               soup.body.find('p', attrs={'class': 'allowance__timespan'})('b')]

            now = datetime.now()
            day = now.day
            month = now.month
            year = now.year
            if day < 2:
                month = now.month - 1
                if month < 1:
                    month += 12
                    year = now.year - 1

            start = datetime(year=year, month=month, day=2)
            total_hours_since_start = ceil((int(now.timestamp()) - int(start.timestamp())) / 3600)
            total_hours_remaining = (days_remaining * 24) + hours_remaining
            hours_in_month = total_hours_since_start + total_hours_remaining
            hour_percentage_passed = round(total_hours_since_start / hours_in_month, 3)
            return hour_percentage_passed * DATA_LIMIT
        except AttributeError:
            sleep(0.5)
            continue


def get_savings():
    while True:
        try:
            res = get('http://add-on.ee.co.uk/mbbstatus', timeout=5)
            soup = BeautifulSoup(res.content, 'html.parser')

            allowance__timespan = soup.body.find('p', attrs={'class': 'allowance__timespan'}).text.strip().lower()

            if 'days' in allowance__timespan:
                days_remaining, hours_remaining = [int(b.text) for b in
                                                   soup.body.find('p', attrs={'class': 'allowance__timespan'})('b')]
                mins_remaining = 0
            elif 'mins' in allowance__timespan:
                days_remaining = 0
                hours_remaining, mins_remaining = [int(b.text) for b in
                                                   soup.body.find('p', attrs={'class': 'allowance__timespan'})('b')]
            else:
                raise ValueError(f'Unknown allowance__timespan element: {allowance__timespan}')

            hours_remaining += mins_remaining / 60

            now = datetime.now()
            day = now.day
            month = now.month
            year = now.year
            if day < 2:
                month = now.month - 1
                if month < 1:
                    month += 12
                    year = now.year - 1

            start = datetime(year=year, month=month, day=2)
            total_hours_since_start = ceil((int(now.timestamp()) - int(start.timestamp())) / 3600)
            total_hours_remaining = (days_remaining * 24) + hours_remaining
            hours_in_month = total_hours_since_start + total_hours_remaining
            hour_percentage_passed = round(total_hours_since_start / hours_in_month, 3)
            allowance = round(hour_percentage_passed * DATA_LIMIT, 1)

            for small in soup('small'):
                small.decompose()
            usage = float(
                sub(r"[\n\t\sA-Za-z]*", "", soup.body.find('span', attrs={'class': 'allowance__left'}).text)
            )

            if usage > DATA_LIMIT:
                usage = usage / 1024

            usage = round(usage, 2)
            savings = round(allowance - (DATA_LIMIT - usage), 2)

            break
        except (AttributeError, ReadTimeout):
            sleep(0.5)
            continue
        except ValueError as e:
            exit(e)

    return savings


def get_used_data():
    return DATA_LIMIT - get_remaining_data()


if __name__ == '__main__':
    print(f'Data allowance: {get_allowance()}GB')
    print(f'Used data: {get_used_data()}GB')
    print(f'Remaining data: {get_remaining_data()}GB')
    print(f'Saved data: {get_savings()}GB')
