from homeassistant.helpers.entity import Entity

REQUIREMENTS = ['beautifulsoup4']


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
            usage = float(
                sub(r"[\n\t\sA-Za-z]*", "", soup.body.find('span', attrs={'class': 'allowance__left'}).text)
            )

            if usage > 200:
                usage = usage / 1024

            return round(usage, 2)
        except (AttributeError, ReadTimeout):
            sleep(1)
            continue


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([RemainingDataSensor(), UsedDataSensor(), ExpectedUsedDataSensor()])


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
        self._state = round(200.00 - _get_remaining_data(), 2)


class ExpectedUsedDataSensor(Entity):
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

        allowance = None
        success = False
        while not success:
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
                allowance = hour_percentage_passed * 200
                success = True
            except (AttributeError, ReadTimeout):
                sleep(0.5)
                continue

        self._state = round(allowance, 1)


