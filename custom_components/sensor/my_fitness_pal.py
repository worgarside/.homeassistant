from datetime import datetime, timedelta
from os import getenv

from dotenv import load_dotenv
from homeassistant.const import MASS_GRAMS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from myfitnesspal import Client

ENV_VARS = '../../secret_files/.env'

load_dotenv(ENV_VARS)

USERNAME = getenv('EMAIL')
PASSWORD = getenv('MFP_PASSWORD')

REQUIREMENTS = ['python-dotenv', 'myfitnesspal']

NOW = datetime.now()

MFP_CLIENT = Client(USERNAME, PASSWORD)
TODAY_MFP = MFP_CLIENT.get_date(NOW.year, NOW.month, NOW.day)


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([CalorieConsumptionSensor()])


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
        self._state = TODAY_MFP.totals.get('calories', 0)


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
        self._state = TODAY_MFP.totals.get('carbohydrates', 0)


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
        self._state = TODAY_MFP.totals.get('fat', 0)


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

    @Throttle(timedelta(minutes=30))
    def update(self):
        self._state = TODAY_MFP.totals.get('protein', 0)


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
        self._state = TODAY_MFP.totals.get('sodium', 0)


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
        self._state = TODAY_MFP.totals.get('sugar', 0)
