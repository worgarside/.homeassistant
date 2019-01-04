from homeassistant.helpers.entity import Entity

REQUIREMENTS = ['beautifulsoup4']


def _get_remaining_data():
    from requests import get
    from re import sub
    from bs4 import BeautifulSoup

    res = get('http://add-on.ee.co.uk/mbbstatus')

    soup = BeautifulSoup(res.content, 'html.parser')
    for small in soup('small'):
        small.decompose()
    usage = float(
        sub(r"[\n\t\sA-Za-z]*", "", soup.body.find('span', attrs={'class': 'allowance__left'}).text)
    )

    if usage > 200:
        usage = usage / 1024

    return round(usage, 2)


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([RemainingDataSensor(), UsedDataSensor()])


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
