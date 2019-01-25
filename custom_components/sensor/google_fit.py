from datetime import datetime, timedelta
from time import mktime

from homeassistant.const import MASS_KILOGRAMS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

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

REQUIREMENTS = ['google-auth-oauthlib', 'google-api-python-client']


def log(m='', newline=False):
    now = datetime.now()
    with open('/home/homeassistant/.homeassistant/logs/hass_activity_{}-{:02d}-{:02d}.log'
                      .format(now.year, now.month, now.day), 'a') as f:
        if newline:
            f.write('\n')
        f.write('\n[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]: {}'
                .format(now.year, now.month, now.day, now.hour, now.minute, now.second, m)
                )


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([DailyStepCountSensor(), CumulativeStepCountSensor(), BodyWeightSensor(), CalorieExpenditureSensor()])


def _get_client():
    from json import load, dump
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from time import sleep
    from ssl import SSLEOFError
    from socket import timeout

    with open(CREDENTIALS_FILE, 'r') as f:
        credentials_dict = load(f)

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
            return build(API_SERVICE_NAME, API_VERSION, credentials=updated_credentials, cache_discovery=False)
        except (SSLEOFError, ConnectionResetError, timeout) as e:
            sleep(2)
            if retry_count < MAX_RETRIES:
                retry_count += 1
                continue
            else:
                exit(e)


def _get_dataset(client, data_source, dataset):
    from ssl import SSLEOFError
    from time import sleep
    from socket import timeout

    retry_count = 0
    while True:
        try:
            dataset = client.users().dataSources().datasets(). \
                get(userId=USER_ID, dataSourceId=data_source, datasetId=dataset).execute()
            return dataset
        except (SSLEOFError, ConnectionResetError, timeout) as e:
            sleep(1)
            if retry_count < MAX_RETRIES:
                retry_count += 1
                continue
            else:
                exit(e)


class DailyStepCountSensor(Entity):
    def __init__(self):
        self._state = None
        self._dataset = None
        self._client = None
        self._data_source = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'

    @property
    def name(self):
        return 'Daily Step Count'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'Steps'

    @Throttle(timedelta(minutes=15))
    def update(self):
        self._client = _get_client()

        now = int(datetime.now().timestamp()) * 1000000000
        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)
        self._dataset = '{}-{}'.format(day_start, now)
        dataset = _get_dataset(self._client, self._data_source, self._dataset)

        step_count = 0
        for point in dataset['point']:
            if int(point['startTimeNanos']) > day_start:
                step_count += point['value'][0]['intVal']

        self._state = step_count
        log('Google Fit: Daily Step Count - {}'.format(self._state))


class CumulativeStepCountSensor(Entity):
    def __init__(self):
        self._client = None
        self._state = None
        self._data_source = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
        self._pkl_file_path = '/home/homeassistant/.homeassistant/custom_components/sensor/vars/cum_step_count.pkl'

    @property
    def name(self):
        return 'Cumulative Step Count'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return 'Steps'

    @Throttle(timedelta(minutes=15))
    def update(self):
        from pickle import load, dump

        self._client = _get_client()

        year_start = 1546304400 * 1000000000
        now = int(datetime.now().timestamp()) * 1000000000
        dataset = _get_dataset(self._client, self._data_source, '{}-{}'.format(year_start, now))

        with open(self._pkl_file_path, 'rb') as f:
            cum_step_count, recent_cum_start_time = load(f)

        for point in dataset['point']:
            if int(point['startTimeNanos']) > recent_cum_start_time:
                cum_step_count += point['value'][0]['intVal']
                recent_cum_start_time = int(point['startTimeNanos'])

        with open(self._pkl_file_path, 'wb') as f:
            dump([cum_step_count, recent_cum_start_time], f)

        self._state = cum_step_count
        log('Google Fit: Cumulative Step Count - {}'.format(self._state))


class BodyWeightSensor(Entity):
    def __init__(self):
        self._client = None
        self._state = None
        self._data_source = 'raw:com.google.weight:com.google.android.apps.fitness:user_input'

    @property
    def name(self):
        return 'Body Weight'

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return MASS_KILOGRAMS

    @Throttle(timedelta(minutes=15))
    def update(self):
        self._client = _get_client()

        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)
        now = int(datetime.now().timestamp()) * 1000000000
        dataset = _get_dataset(self._client, self._data_source,'{}-{}'.format(day_start, now))

        if len(dataset['point']) == 1:
            self._state = round(dataset['point'][0]['value'][0]['fpVal'], 2)
            log('Google Fit: Body Weight - {}'.format(self._state))
        elif len(dataset['point']) > 1:
            max_time = 0
            weight = 0
            for point in dataset['point']:
                if float(point['endTimeNanos']) > max_time:
                    max_time = float(point['endTimeNanos'])
                    weight = point['value'][0]['fpVal']

            self._state = round(weight, 2) if not weight == 0 else None
            log('Google Fit: Body Weight - {}'.format(self._state))


class CalorieExpenditureSensor(Entity):
    def __init__(self):
        self._client = None
        self._state = None
        self._data_source = 'derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended'

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
        self._client = _get_client()

        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)
        now = int(datetime.now().timestamp()) * 1000000000
        dataset = _get_dataset(self._client, self._data_source, '{}-{}'.format(day_start, now))

        cal_count = 0
        for point in dataset['point']:
            if int(point['startTimeNanos']) > day_start:
                cal_count += point['value'][0]['fpVal']

        self._state = int(cal_count)
        log('Google Fit: Calories Expended - {}'.format(self._state))
