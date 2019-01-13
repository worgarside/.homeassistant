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

REQUIREMENTS = ['google-auth-oauthlib', 'google-api-python-client']


def log(m='', newline=False):
    now = datetime.now()
    with open('/home/homeassistant/.homeassistant/hass_activity_{}-{:02d}-{:02d}.log'.format(now.year, now.month, now.day),
              'a') as f:
        if newline:
            f.write('\n')
        f.write('\n[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]: {}'
                .format(now.year, now.month, now.day, now.hour, now.minute, now.second, m)
                )


def setup_platform(hass, config, add_devices, discovery_info=None):
    add_devices([DailyStepCountSensor(), CumulativeStepCountSensor(), BodyWeightSensor(), CalorieExpenditureSensor()])


def _get_client(credentials_dict):
    from json import dump
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from time import sleep
    from ssl import SSLEOFError
    from socket import timeout

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
        from json import load

        now = int(datetime.now().timestamp())
        now_nano = now * 1000000000
        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)

        self._state = None
        self._data_source = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
        self._dataset = '{}-{}'.format(day_start, now_nano)
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
        log('Google Fit: Daily Step Count')

        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)
        dataset = _get_dataset(self._client, self._data_source, self._dataset)

        step_count = 0
        for point in dataset['point']:
            if int(point['startTimeNanos']) > day_start:
                step_count += point['value'][0]['intVal']

        self._state = step_count


class CumulativeStepCountSensor(Entity):
    def __init__(self):
        from json import load

        now = int(datetime.now().timestamp())
        now_nano = now * 1000000000
        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)

        self._state = None
        self._data_source = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
        self._dataset = '{}-{}'.format(day_start, now_nano)
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
        log('Google Fit: Cumulative Step Count')
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

        now = int(datetime.now().timestamp())
        now_nano = now * 1000000000
        one_hour_ago = (now - 3600) * 1000000000

        self._state = None
        self._data_source = 'raw:com.google.weight:com.google.android.apps.fitness:user_input'
        self._dataset = '{}-{}'.format(one_hour_ago, now_nano)
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

    @Throttle(timedelta(minutes=5))
    def update(self):
        log('Google Fit: Body Weight')
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
            self._state = round(weight, 2) if not weight == 0 else None


class CalorieExpenditureSensor(Entity):
    def __init__(self):
        from json import load

        now = int(datetime.now().timestamp())
        now_nano = now * 1000000000
        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)

        self._state = None
        self._data_source = 'derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended'
        self._dataset = '{}-{}'.format(day_start, now_nano)
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

    @Throttle(timedelta(minutes=5))
    def update(self):
        log('Google Fit: Calories Expended')

        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)
        dataset = _get_dataset(self._client, self._data_source, self._dataset)

        cal_count = 0
        for point in dataset['point']:
            if int(point['startTimeNanos']) > day_start:
                cal_count += point['value'][0]['fpVal']

        self._state = int(cal_count)
