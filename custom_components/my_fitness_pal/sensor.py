from datetime import datetime, timedelta
from os import getenv, path

from dotenv import load_dotenv
from homeassistant.const import MASS_GRAMS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

REQUIREMENTS = ['myfitnesspal', 'python-dotenv']

HOME_ASSISTANT = '.homeassistant'
DIRNAME, _ = path.split(path.abspath(__file__))
HASS_DIR = DIRNAME[:DIRNAME.find(HOME_ASSISTANT) + len(HOME_ASSISTANT)] + '/'
SECRET_FILES_DIR = '{}secret_files/'.format(HASS_DIR)
LOG_DIRECTORY = '{}logs/'.format(HASS_DIR)

load_dotenv('{}.env'.format(SECRET_FILES_DIR))

EMAIL = getenv('EMAIL')
PASSWORD = getenv('MFP_PASSWORD')
MAX_RETRIES = 5


def log(m='', newline=False):
    now = datetime.now()

    with open('{}hass_activity_{}-{:02d}-{:02d}.log'.format(LOG_DIRECTORY, now.year, now.month, now.day), 'a') as f:
        if newline:
            f.write('\n')
        f.write('\n[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]: {}'
                .format(now.year, now.month, now.day, now.hour, now.minute, now.second, m)
                )


def _get_total(food_group):
    from myfitnesspal import Client
    from json.decoder import JSONDecodeError
    from time import sleep

    log('MFP: {}'.format(food_group))
    now = datetime.now()
    retry_count = 0
    while True:
        try:
            return Client(EMAIL, PASSWORD) \
                .get_date(now.year, now.month, now.day) \
                .totals \
                .get(food_group, 0)
        except JSONDecodeError:
            sleep(2)
            if retry_count < MAX_RETRIES:
                retry_count += 1
                continue
            else:
                exit()


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([CalorieConsumptionSensor(), CarbohydrateConsumptionSensor(), FatConsumptionSensor(),
                 ProteinConsumptionSensor(), SodiumConsumptionSensor(), SugarConsumptionSensor()])


class CalorieConsumptionSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Calories Consumed'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'kcal'

    @Throttle(timedelta(minutes=30))
    def update(self):
        self._state = _get_total('calories')


class CarbohydrateConsumptionSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Carbohydrates Consumed'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return MASS_GRAMS

    @Throttle(timedelta(minutes=30))
    def update(self):
        self._state = _get_total('carbohydrates')


class FatConsumptionSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Fat Consumed'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return MASS_GRAMS

    @Throttle(timedelta(minutes=30))
    def update(self):
        self._state = _get_total('fat')


class ProteinConsumptionSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Protein Consumed'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return MASS_GRAMS

    @Throttle(timedelta(minutes=10))
    def update(self):
        self._state = _get_total('protein')


class SodiumConsumptionSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Sodium Consumed'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return MASS_GRAMS

    @Throttle(timedelta(minutes=30))
    def update(self):
        self._state = round(_get_total('sodium') / 1000.0, 2)


class SugarConsumptionSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Sugar Consumed'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return MASS_GRAMS

    @Throttle(timedelta(minutes=30))
    def update(self):
        _get_total('sugar')
