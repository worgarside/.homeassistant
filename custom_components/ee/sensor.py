from os import getenv, path
from wg_utilities.references.constants import HOMEASSISTANT, BS4_PARSER
from dotenv import load_dotenv
from homeassistant.helpers.entity import Entity
from wg_utilities.helpers.functions import get_proj_dirs
from wg_utilities.services.services import pb_notify

REQUIREMENTS = ['beautifulsoup4', 'python-dotenv', 'wg-utilities']

_, _, ENV_FILE = get_proj_dirs(path.abspath(__file__), HOMEASSISTANT)
load_dotenv(ENV_FILE)

PB_API_KEY = getenv('PB_API_KEY')
DATA_LIMIT = 300.00

EE_URL = 'http://add-on.ee.co.uk/mbbstatus'


def _get_allowance():
    from requests import get
    from bs4 import BeautifulSoup
    from datetime import datetime
    from math import ceil

    res = get(EE_URL, timeout=5)
    soup = BeautifulSoup(res.content, BS4_PARSER)

    refined_soup = soup.body.find('p', attrs={'class': 'allowance__timespan'})

    allowance__timespan = refined_soup.text.strip().lower()

    days_remaining = 0
    hours_remaining = 0
    mins_remaining = 0
    if 'days' in allowance__timespan or 'day' in allowance__timespan:
        days_remaining, hours_remaining = [int(b.text) for b in refined_soup('b')]
    elif 'mins' in allowance__timespan or 'min' in allowance__timespan:
        if len(refined_soup('b')) == 2:
            hours_remaining, mins_remaining = [int(b.text) for b in refined_soup('b')]
        elif len(refined_soup('b')) == 1:
            mins_remaining = [int(b.text) for b in refined_soup('b')]
        else:
            raise ValueError('Unknown allowance__timespan element: {}'.format(allowance__timespan.strip()))
    elif len(refined_soup('b')) == 1 \
            and ('days' not in allowance__timespan or 'day' not in allowance__timespan) \
            and ('mins' not in allowance__timespan or 'min' not in allowance__timespan):
        hours_remaining = [int(b.text) for b in refined_soup('b')]
    else:
        raise ValueError('Unknown allowance__timespan element: {}'.format(allowance__timespan.strip()))

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
    return round(hour_percentage_passed * DATA_LIMIT, 1), soup


def _get_remaining_data():
    from requests import get, ReadTimeout
    from re import sub
    from bs4 import BeautifulSoup
    from time import sleep

    while True:
        try:
            res = get(EE_URL, timeout=5)

            soup = BeautifulSoup(res.content, BS4_PARSER)
            for small in soup('small'):
                small.decompose()

            allowance__left = soup.body.find('span', attrs={'class': 'allowance__left'}).text
            usage = float(
                sub(r"[\n\t\sA-Za-z]*", "", allowance__left)
            )

            if 'gb' not in allowance__left.lower() and 'mb' in allowance__left.lower():
                usage /= 1024
            elif 'gb' not in allowance__left.lower() and 'mb' not in allowance__left.lower():
                raise ValueError('Unknown allowance__left element: {}'.format(allowance__left.strip()))

            return round(usage, 2)
        except (AttributeError, ReadTimeout):
            sleep(1)
            continue
        except ValueError as e:
            pb_notify(t='EE Data Savings Sensor Error', m=str(e), token=PB_API_KEY)
            exit(1)


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
        from requests import ReadTimeout
        from time import sleep

        while True:
            try:
                allowance, _ = _get_allowance()
                break
            except (AttributeError, ReadTimeout):
                sleep(0.5)
                continue
            except ValueError as e:
                pb_notify(t='EE Data Savings Sensor Error', m=str(e), token=PB_API_KEY)
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
        from requests import ReadTimeout
        from time import sleep
        from re import sub
        while True:
            try:
                allowance, soup = _get_allowance()

                for small in soup('small'):
                    small.decompose()
                usage = float(
                    sub(r"[\n\t\sA-Za-z]*", "", soup.body.find('span', attrs={'class': 'allowance__left'}).text)
                )

                if usage > DATA_LIMIT:
                    usage /= 1024

                usage = round(usage, 2)
                savings = round(allowance - (DATA_LIMIT - usage), 2)

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
