from homeassistant.helpers.entity import Entity

from dotenv import load_dotenv
from os import getenv

REQUIREMENTS = ['beautifulsoup4', 'python-dotenv']

load_dotenv('/home/homeassistant/.homeassistant/secret_files/.env')

PB_API_KEY = getenv('PB_API_KEY')
DATA_LIMIT = 200.00


def _get_remaining_data():
    from requests import get, ReadTimeout
    from re import sub
    from bs4 import BeautifulSoup
    from time import sleep

    while True:
        try:
            res = get('http://add-on.ee.co.uk/mbbstatus', timeout=5)

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
                raise ValueError('Unknown allowance__left element: {}'.format(allowance__left))

            return round(usage, 2)
        except (AttributeError, ReadTimeout):
            sleep(1)
            continue
        except ValueError as e:
            _send_notification('EE Data Savings Sensor Error', e)
            exit(1)


def _send_notification(t, m):
    from requests import post
    post(
        'https://api.pushbullet.com/v2/pushes',
        headers={
            'Access-Token': PB_API_KEY,
            'Content-Type': 'application/json'
        },
        json={
            'body': m,
            'title': t,
            'type': 'note'
        }
    )


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([RemainingDataSensor(), UsedDataSensor(), DataAllowanceSensor(), DataSavingsSensor(),
                 DataLimitSensor()])


class RemainingDataSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Remaining Data'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'GB'

    def update(self):
        self._state = _get_remaining_data()


class UsedDataSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Used Data'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'GB'

    def update(self):
        self._state = round(DATA_LIMIT - _get_remaining_data(), 2)


class DataAllowanceSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Data Allowance'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'GB'

    def update(self):
        from requests import get, ReadTimeout
        from bs4 import BeautifulSoup
        from datetime import datetime
        from math import ceil
        from time import sleep

        while True:
            try:
                res = get('http://add-on.ee.co.uk/mbbstatus', timeout=5)
                soup = BeautifulSoup(res.content, 'html.parser')
                allowance_left = soup.body.find('p', attrs={'class': 'allowance__timespan'}).text.strip().lower()

                if 'days' in allowance_left:
                    days_remaining, hours_remaining = [int(b.text) for b in
                                                       soup.body.find('p', attrs={'class': 'allowance__timespan'})('b')]
                    mins_remaining = 0
                elif 'mins' in allowance_left:
                    days_remaining = 0
                    hours_remaining, mins_remaining = [int(b.text) for b in
                                                       soup.body.find('p', attrs={'class': 'allowance__timespan'})('b')]
                else:
                    raise ValueError('Unknown allowance_left element: {}'.format(allowance_left))

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
                break
            except (AttributeError, ReadTimeout):
                sleep(0.5)
                continue
            except ValueError as e:
                _send_notification('EE Data Savings Sensor Error', e)
                allowance = None
                break

        self._state = allowance


class DataSavingsSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Data Savings'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'GB'

    def update(self):
        from requests import get, ReadTimeout
        from bs4 import BeautifulSoup
        from datetime import datetime
        from math import ceil
        from time import sleep
        from re import sub
        from pickle import dump, load
        while True:
            try:
                res = get('http://add-on.ee.co.uk/mbbstatus', timeout=5)
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

                if savings < 2:
                    pkl_file_path = '/home/homeassistant/.homeassistant/custom_components/sensor/vars/ee_allowance_notif_time.pkl'
                    with open(pkl_file_path, 'rb') as f:
                        last_time = load(f)

                    if (datetime.now() - last_time) > 21600:
                        _send_notification('EE Data Warning', 'Your data savings has dropped below 2GB: {}'.format(savings))
                        with open(pkl_file_path, 'wb') as f:
                            dump(datetime.now(), f)

                break
            except (AttributeError, ReadTimeout):
                sleep(0.5)
                continue

        self._state = savings


class DataLimitSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Data Limit'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'GB'

    def update(self):
        self._state = DATA_LIMIT
