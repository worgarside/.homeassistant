from datetime import datetime, timedelta
from os import path, getenv

from dotenv import load_dotenv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from wg_utilities.helpers.functions import get_proj_dirs
from wg_utilities.references.constants import HOMEASSISTANT

_, _, ENV_FILE = get_proj_dirs(path.abspath(__file__), HOMEASSISTANT)

load_dotenv(ENV_FILE)

HASS_DB_URL = getenv('HASS_DB_URL')


def _castable(value, typ):
    try:
        typ(value)
        return True
    except ValueError:
        return False


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([DailyStepCountSummarySensor()])


class DailyStepCountSummarySensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Daily Step Count Summary'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'Steps'

    @Throttle(timedelta(minutes=15))
    def update(self):
        now = datetime.now()
        if not (now.hour == 23 and 45 <= now.minute <= 59):
            self._state = None
        else:
            from psycopg2 import connect

            con = connect(HASS_DB_URL)
            cur = con.cursor()
            cur.execute("""
                SELECT state
                FROM states
                WHERE entity_id = 'sensor.daily_step_count'
                  AND last_changed::DATE = '{}';
            """.format(now.strftime('%Y-%m-%d')))

            states = [int(t[0]) for t in cur.fetchall() if _castable(t[0], int)]

            self._state = max(states)
