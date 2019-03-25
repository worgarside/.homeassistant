from datetime import datetime, timedelta
from os import getenv, path

from dotenv import load_dotenv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from wg_utilities.references.constants import HOMEASSISTANT
from wg_utilities.helpers.functions import get_proj_dirs

REQUIREMENTS = ['wg-utilities', 'python-dotenv', 'requests']

PROJECT_DIR, SECRET_FILES_DIR, ENV_FILE = get_proj_dirs(path.abspath(__file__), HOMEASSISTANT)
LOG_DIRECTORY = '{}logs/'.format(PROJECT_DIR)
ENDPOINT = 'https://api.monzo.com/'

load_dotenv('{}.env'.format(SECRET_FILES_DIR))

MONZO_CLIENT_SECRET = getenv('MONZO_CLIENT_SECRET')
MONZO_ACCT_ID = getenv('MONZO_ACCOUNT_ID')
CREDENTIALS_FILE = '{}monzo_client_secrets.json'.format(SECRET_FILES_DIR)


def log(m='', newline=False):
    now = datetime.now()

    with open('{}hass_activity_{}-{:02d}-{:02d}.log'.format(LOG_DIRECTORY, now.year, now.month, now.day), 'a') as f:
        if newline:
            f.write('\n')
        f.write('\n[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]: {}'
                .format(now.year, now.month, now.day, now.hour, now.minute, now.second, m)
                )


def authorize(refresh=False):
    from json import load, dump
    with open(CREDENTIALS_FILE) as f:
        secrets = load(f)

    if refresh:
        from requests import post

        credentials = {
            'grant_type': 'refresh_token',
            'client_secret': MONZO_CLIENT_SECRET,
            'client_id': secrets['client_id'],
            'refresh_token': secrets['refresh_token']
        }

        res = post('https://api.monzo.com/oauth2/token', data=credentials)

        if not res.status_code == 200:
            log('Unable to refresh Monzo API token')
            # TODO replace with ex-backoff
            raise OSError(str(res.json()))

        secrets = res.json()

        with open(CREDENTIALS_FILE, 'w') as f:
            dump(secrets, f)

    return secrets['access_token']


def _get_balance(key):
    from requests import get

    h = {'Authorization': 'Bearer {}'.format(authorize())}
    json = get('{}balance?account_id={}'.format(ENDPOINT, MONZO_ACCT_ID), headers=h).json()

    try:
        return json[key]
    except KeyError:
        h = {'Authorization': 'Bearer {}'.format(authorize(refresh=True))}
        json = get('{}balance?account_id={}'.format(ENDPOINT, MONZO_ACCT_ID), headers=h).json()
        return json[key]


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([MonzoCurrentAccountBalanceSensor(), MonzoTotalBalanceSensor()])


class MonzoCurrentAccountBalanceSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Monzo Current Account Balance'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'GBP'

    @Throttle(timedelta(minutes=10))
    def update(self):
        self._state = round(_get_balance('balance') / 100, 2)


class MonzoTotalBalanceSensor(Entity):
    def __init__(self):
        self._state = None

    @property
    def name(self):
        return 'Monzo Total Balance'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'GBP'

    @Throttle(timedelta(minutes=10))
    def update(self):
        self._state = round(_get_balance('total_balance') / 100, 2)
