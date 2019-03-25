from datetime import datetime, timedelta
from os import getenv, path

from dotenv import load_dotenv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from wg_utilities.references.constants import HOMEASSISTANT
from wg_utilities.helpers.functions import get_proj_dirs, log

REQUIREMENTS = ['wg-utilities', 'python-dotenv', 'requests']

PROJECT_DIR, SECRET_FILES_DIR, ENV_FILE = get_proj_dirs(path.abspath(__file__), HOMEASSISTANT)
ENDPOINT = 'https://api.monzo.com/'

load_dotenv('{}.env'.format(SECRET_FILES_DIR))

MONZO_CLIENT_SECRET = getenv('MONZO_CLIENT_SECRET')
MONZO_ACCT_ID = getenv('MONZO_ACCOUNT_ID')
CREDENTIALS_FILE = '{}monzo_client_secrets.json'.format(SECRET_FILES_DIR)
PSQL_CREDS = {
    'db_user': getenv('HASS_DB_USER'),
    'db_password': getenv('HASS_DB_PASSWORD'),
    'db_host': getenv('HASSPI_LOCAL_IP'),
    'db_name': getenv('SECONDARY_DB_NAME')
}


def authorize(refresh=False):
    from json import load, dump
    with open(CREDENTIALS_FILE) as f:
        secrets = load(f)

    if refresh:
        from requests import post
        log(db_creds=PSQL_CREDS, description='Refreshing Monzo API credentials')

        credentials = {
            'grant_type': 'refresh_token',
            'client_secret': MONZO_CLIENT_SECRET,
            'client_id': secrets['client_id'],
            'refresh_token': secrets['refresh_token']
        }

        res = post('https://api.monzo.com/oauth2/token', data=credentials)

        if not res.status_code == 200:
            log(db_creds=PSQL_CREDS,
                description='Unable to refresh Monzo API credentials',
                json_content={'status_code': res.status_code, 'reason': res.reason}
                )
            # TODO replace with ex-backoff
            raise OSError(str(res.json()))

        secrets = res.json()

        with open(CREDENTIALS_FILE, 'w') as f:
            dump(secrets, f)
            log(db_creds=PSQL_CREDS, description='Monzo API credentials refreshed successfully')

    return secrets['access_token']


def _get_balance(key, refresh_auth=False):
    from requests import get

    h = {'Authorization': 'Bearer {}'.format(authorize(refresh=refresh_auth))}
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

    # @Throttle(timedelta(minutes=10))
    def update(self):
        try:
            self._state = round(_get_balance('balance') / 100, 2)
        except KeyError:
            self._state = round(_get_balance('balance', refresh_auth=True) / 100, 2)


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

    # @Throttle(timedelta(minutes=10))
    def update(self):
        try:
            self._state = round(_get_balance('total_balance') / 100, 2)
        except KeyError:
            self._state = round(_get_balance('total_balance', refresh_auth=True) / 100, 2)
