from datetime import datetime, timedelta
from os import getenv

from dotenv import load_dotenv
from homeassistant.const import MASS_GRAMS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

REQUIREMENTS = ['myfitnesspal', 'python-dotenv']

load_dotenv('/home/homeassistant/.homeassistant/secret_files/.env')
EMAIL = getenv('EMAIL')
PASSWORD = getenv('MFP_PASSWORD')


def log(m='', newline=False):
    now = datetime.now()

    with open('/home/pi/Projects/wg-utils/logs/hass_activity_{}-{:02d}-{:02d}.log'.format(now.year, now.month, now.day),
              'a') as f:
        if newline:
            f.write('\n')
        f.write('\n[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]: {}'
                .format(now.year, now.month, now.day, now.hour, now.minute, now.second, m)
                )


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
        log('MFP: Calories')
        from myfitnesspal import Client
        now = datetime.now()

        self._state = Client(EMAIL, PASSWORD) \
            .get_date(now.year, now.month, now.day) \
            .totals \
            .get('calories', 0)


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
        log('MFP: Carbohydrates')
        from myfitnesspal import Client
        now = datetime.now()

        self._state = Client(EMAIL, PASSWORD) \
            .get_date(now.year, now.month, now.day) \
            .totals \
            .get('carbohydrates', 0)


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
        log('MFP: Fat')
        from myfitnesspal import Client
        now = datetime.now()

        self._state = Client(EMAIL, PASSWORD) \
            .get_date(now.year, now.month, now.day) \
            .totals \
            .get('fat', 0)


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
        log('MFP: Protein')
        from myfitnesspal import Client
        now = datetime.now()

        self._state = Client(EMAIL, PASSWORD) \
            .get_date(now.year, now.month, now.day) \
            .totals \
            .get('protein', 0)


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
        log('MFP: Sodium')
        from myfitnesspal import Client
        now = datetime.now()

        self._state = round(Client(EMAIL, PASSWORD)
                            .get_date(now.year, now.month, now.day)
                            .totals
                            .get('sodium', 0) / 1000.0, 2)


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
        log('MFP: Sugar')
        from myfitnesspal import Client
        now = datetime.now()

        self._state = Client(EMAIL, PASSWORD) \
            .get_date(now.year, now.month, now.day) \
            .totals \
            .get('sugar', 0)
