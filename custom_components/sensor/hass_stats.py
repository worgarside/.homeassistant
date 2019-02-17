from os import getenv, path

from dotenv import load_dotenv
from homeassistant.helpers.entity import Entity

REQUIREMENTS = ['python-dotenv', 'psycopg2-binary']

HOME_ASSISTANT = '.homeassistant'
DIRNAME, _ = path.split(path.abspath(__file__))
HASS_DIR = DIRNAME[:DIRNAME.find(HOME_ASSISTANT) + len(HOME_ASSISTANT)] + '/'
SECRET_FILES_DIR = '{}secret_files/'.format(HASS_DIR)

load_dotenv('{}.env'.format(SECRET_FILES_DIR))

HASS_DB_URL = getenv('HASS_DB_URL')


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([DatabaseDiskSizeSensor(), DatabaseRowCountSensor()])


class DatabaseDiskSizeSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'DB Size'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'GB'

    def update(self):
        from psycopg2 import connect

        con = connect(HASS_DB_URL)
        cur = con.cursor()
        cur.execute("SELECT pg_database_size('homeassistant');")

        self._state = round(int(cur.fetchone()[0]) / 1024 ** 3, 4)


class DatabaseRowCountSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'DB Size'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'rows'

    def update(self):
        from psycopg2 import connect

        con = connect(HASS_DB_URL)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM states")

        self._state = int(cur.fetchone()[0])
