from datetime import datetime, timedelta
from time import mktime

from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.const import MASS_KILOGRAMS

CLIENT_SECRETS_FILE = '/home/homeassistant/.homeassistant/secret_files/google_client_secrets.json'
CREDENTIALS_FILE = '/home/homeassistant/.homeassistant/secret_files/google_credentials.json'

USER_ID = 'me'
API_SERVICE_NAME = 'fitness'
API_VERSION = 'v1'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
SCOPES = ['https://www.googleapis.com/auth/fitness.activity.read',
          'https://www.googleapis.com/auth/fitness.body.read',
          'https://www.googleapis.com/auth/fitness.location.read',
          'https://www.googleapis.com/auth/fitness.nutrition.read']
MAX_RETRIES = 5

NOW = int(datetime.now().timestamp())
NOW_NANO = NOW * 1000000000
DAY_START = int(mktime(datetime.today().date().timetuple()) * 1000000000)
ONE_HOUR_AGO = (NOW - 3600) * 1000000000
TWO_MINS_AGO = (NOW - 120) * 1000000000

REQUIREMENTS = ['google-auth-oauthlib', 'google-api-python-client']


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([DailyStepCountSensor(), CumulativeStepCountSensor(), BodyWeightSensor(), CalorieExpenditureSensor(),
                 SpeedSensor()])


def _get_client(credentials_dict):
    from json import dump
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from time import sleep
    from ssl import SSLEOFError

    updated_credentials = Credentials(
        credentials_dict['token'],
        credentials_dict['refresh_token'],
        '',
        credentials_dict['token_uri'],
        credentials_dict['client_id'],
        credentials_dict['client_secret'],
        credentials_dict['scopes']
    )
    with open(CREDENTIALS_FILE, 'w') as f:
        dump({'token': updated_credentials.token,
              'refresh_token': updated_credentials.refresh_token,
              'token_uri': updated_credentials.token_uri,
              'client_id': updated_credentials.client_id,
              'client_secret': updated_credentials.client_secret,
              'scopes': updated_credentials.scopes}, f)

    retry_count = 0
    while True:
        try:
            client = build(API_SERVICE_NAME, API_VERSION, credentials=updated_credentials, cache_discovery=False)
            return client
        except SSLEOFError as e:
            sleep(2.5)
            if retry_count < MAX_RETRIES:
                retry_count += 1
                continue
            else:
                raise SSLEOFError(e)


def _get_dataset(client, data_source, dataset):
    from ssl import SSLEOFError
    from time import sleep

    retry_count = 0
    while True:
        try:
            dataset = client.users().dataSources().datasets(). \
                get(userId=USER_ID, dataSourceId=data_source, datasetId=dataset).execute()
            return dataset
        except SSLEOFError as e:
            sleep(2.5)
            if retry_count < MAX_RETRIES:
                retry_count += 1
                continue
            else:
                raise SSLEOFError(e)


class DailyStepCountSensor(Entity):
    def __init__(self):
        from json import load

        self._state = None
        self._data_source = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
        self._dataset = '{}-{}'.format(DAY_START, NOW_NANO)
        with open(CREDENTIALS_FILE, 'r') as f:
            self._credentials = load(f)
        self._client = _get_client(self._credentials)

    @property
    def name(self):
        return 'Daily Step Count'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'Steps'

    @Throttle(timedelta(minutes=5))
    def update(self):
        dataset = _get_dataset(self._client, self._data_source, self._dataset)

        step_count = 0
        for point in dataset['point']:
            if int(point['startTimeNanos']) > DAY_START:
                step_count += point['value'][0]['intVal']

        self._state = step_count


class CumulativeStepCountSensor(Entity):
    def __init__(self):
        from json import load

        self._state = None
        self._data_source = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
        self._dataset = '{}-{}'.format(DAY_START, NOW_NANO)
        with open(CREDENTIALS_FILE, 'r') as f:
            self._credentials = load(f)
        self._client = _get_client(self._credentials)

    @property
    def name(self):
        return 'Cumulative Step Count'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'Steps'

    @Throttle(timedelta(minutes=5))
    def update(self):
        from pickle import load, dump

        pkl_file_path = '/home/homeassistant/.homeassistant/custom_components/sensor/vars/cum_step_count.pkl'
        dataset = _get_dataset(self._client, self._data_source, self._dataset)

        with open(pkl_file_path, 'rb') as f:
            cum_step_count, recent_cum_start_time = load(f)

        for point in dataset['point']:
            if int(point['startTimeNanos']) > recent_cum_start_time:
                cum_step_count += point['value'][0]['intVal']
                recent_cum_start_time = int(point['startTimeNanos'])

        with open(pkl_file_path, 'wb') as f:
            dump([cum_step_count, recent_cum_start_time], f)

        self._state = cum_step_count


class BodyWeightSensor(Entity):
    def __init__(self):
        from json import load

        self._state = None
        self._data_source = 'raw:com.google.weight:com.google.android.apps.fitness:user_input'
        self._dataset = '{}-{}'.format(ONE_HOUR_AGO, NOW_NANO)
        with open(CREDENTIALS_FILE, 'r') as f:
            self._credentials = load(f)

        self._client = _get_client(self._credentials)

    @property
    def name(self):
        return 'Body Weight'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return MASS_KILOGRAMS

    @Throttle(timedelta(minutes=60))
    def update(self):

        dataset = _get_dataset(self._client, self._data_source, self._dataset)

        if len(dataset['point']) == 1:
            self._state = dataset['point'][0]['value'][0]['fpVal']
        elif len(dataset['point']) > 1:
            max_time = 0
            weight = 0
            for point in dataset['point']:
                if float(point['endTimeNanos']) > max_time:
                    max_time = float(point['endTimeNanos'])
                    weight = point['value'][0]['fpVal']
            self._state = weight if not weight == 0 else self._state


class CalorieExpenditureSensor(Entity):
    def __init__(self):
        from json import load

        self._state = None
        self._data_source = 'derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended'
        self._dataset = '{}-{}'.format(DAY_START, NOW_NANO)
        with open(CREDENTIALS_FILE, 'r') as f:
            self._credentials = load(f)

        self._client = _get_client(self._credentials)

    @property
    def name(self):
        return 'Calories Expended'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'kcal'

    @Throttle(timedelta(minutes=15))
    def update(self):
        dataset = _get_dataset(self._client, self._data_source, self._dataset)

        cal_count = 0
        for point in dataset['point']:
            if int(point['startTimeNanos']) > DAY_START:
                cal_count += point['value'][0]['fpVal']

        self._state = int(cal_count)


class SpeedSensor(Entity):
    def __init__(self):
        from json import load

        self._state = None
        self._data_source = 'derived:com.google.speed:com.google.android.gms:merge_speed'
        self._dataset = '{}-{}'.format(TWO_MINS_AGO, NOW_NANO)
        with open(CREDENTIALS_FILE, 'r') as f:
            self._credentials = load(f)

        self._client = _get_client(self._credentials)

    @property
    def name(self):
        return 'Instantaneous Speed Over Ground'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'm/s'

    def update(self):

        dataset = _get_dataset(self._client, self._data_source, self._dataset)

        if len(dataset['point']) == 1 and int(dataset['point'][0]['startTimeNanos']) > DAY_START:
            self._state = dataset['point'][0]['value'][0]['fpVal']
        elif len(dataset['point']) > 1:
            max_time = 0
            speed = 0
            for point in dataset['point']:
                if int(point['startTimeNanos']) > DAY_START:
                    if float(point['endTimeNanos']) > max_time:
                        max_time = float(point['endTimeNanos'])
                        speed = point['value'][0]['fpVal']

            self._state = int(speed)
        else:
            self._state = 0
