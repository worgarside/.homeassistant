from datetime import datetime, timedelta
from os import path
from time import mktime

from homeassistant.const import MASS_KILOGRAMS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

REQUIREMENTS = ['google-auth-oauthlib', 'google-api-python-client']

HOME_ASSISTANT = '.homeassistant'
DIRNAME, _ = path.split(path.abspath(__file__))
HASS_DIR = DIRNAME[:DIRNAME.find(HOME_ASSISTANT) + len(HOME_ASSISTANT)] + '/'
SECRET_FILES_DIR = '{}secret_files/'.format(HASS_DIR)
LOG_DIRECTORY = '{}logs/'.format(HASS_DIR)

CLIENT_SECRETS_FILE = '{}google_client_secrets.json'.format(SECRET_FILES_DIR)
CREDENTIALS_FILE = '{}google_credentials.json'.format(SECRET_FILES_DIR)

USER_ID = 'me'
API_SERVICE_NAME = 'fitness'
API_VERSION = 'v1'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
SCOPES = ['https://www.googleapis.com/auth/fitness.activity.read',
          'https://www.googleapis.com/auth/fitness.body.read',
          'https://www.googleapis.com/auth/fitness.location.read',
          'https://www.googleapis.com/auth/fitness.nutrition.read']
MAX_RETRIES = 5


def log(m='', log_dir=LOG_DIRECTORY, file_prefix='hass_activity', newline=False):
    n = datetime.now()
    with open(
            '{}{}_{}-{:02d}-{:02d}.log'.format(log_dir, file_prefix, n.year, n.month, n.day),
            'a') as f:
        if newline:
            f.write('\n')
        f.write('\n[{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]: {}'
                .format(n.year, n.month, n.day, n.hour, n.minute, n.second, m)
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


def _get_dataset(data_source, dataset_start=None, dataset_end=None):
    from ssl import SSLEOFError
    from time import sleep
    from socket import timeout

    dataset_start = int(
        mktime(datetime.today().date().timetuple()) * 1000000000) if not dataset_start else dataset_start
    dataset_end = int(datetime.now().timestamp()) * 1000000000 if not dataset_end else dataset_end

    dataset_range = '{}-{}'.format(dataset_start, dataset_end)
    client = _get_client()

    retry_count = 0
    while True:
        try:
            dataset = client.users().dataSources().datasets(). \
                get(userId=USER_ID, dataSourceId=data_source, datasetId=dataset_range).execute()
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
        dataset = _get_dataset(self._data_source)
        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)
        step_count = 0
        for point in dataset['point']:
            if int(point['startTimeNanos']) > day_start:
                step_count += point['value'][0]['intVal']

        self._state = step_count
        log('Google Fit: Daily Step Count - {}'.format(self._state))


class CumulativeStepCountSensor(Entity):
    def __init__(self):
        self._state = None
        self._data_source = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
        self._pkl_file_path = '{}custom_components/sensor/vars/cum_step_count.pkl'.format(HASS_DIR)

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

        year_start = 1546304400 * 1000000000
        dataset = _get_dataset(self._data_source, dataset_start=year_start)

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
        self._state = None
        self._google_fit_data_source = 'raw:com.google.weight:com.google.android.apps.fitness:user_input'
        self._myfitnesspal_data_source = 'raw:com.google.weight:com.myfitnesspal.android:'

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
        google_fit_dataset = _get_dataset(self._google_fit_data_source)
        myfitnesspal_dataset = _get_dataset(self._myfitnesspal_data_source)

        combined_datapoints = google_fit_dataset['point'] + myfitnesspal_dataset['point']

        if len(combined_datapoints) == 1:
            self._state = round(combined_datapoints[0]['value'][0]['fpVal'], 2)
            log('Google Fit: Body Weight - {}'.format(self._state))
        elif len(combined_datapoints) > 1:
            max_time = 0
            weight = 0
            for point in combined_datapoints:
                if float(point['endTimeNanos']) > max_time:
                    max_time = float(point['endTimeNanos'])
                    weight = point['value'][0]['fpVal']
            self._state = round(weight, 2) if not weight == 0 else self._state
            log('Google Fit: Body Weight - {}'.format(self._state))


class CalorieExpenditureSensor(Entity):
    def __init__(self):
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
        dataset = _get_dataset(self._data_source)
        day_start = int(mktime(datetime.today().date().timetuple()) * 1000000000)
        cal_count = 0
        for point in dataset['point']:
            if int(point['startTimeNanos']) > day_start:
                cal_count += point['value'][0]['fpVal']

        self._state = int(cal_count)
        log('Google Fit: Calories Expended - {}'.format(self._state))
