from psycopg2 import connect
from datetime import datetime
from os import path, getenv
from dotenv import load_dotenv

HOME_ASSISTANT = '.homeassistant'
DIRNAME, _ = path.split(path.abspath(__file__))
HASS_DIR = DIRNAME[:DIRNAME.find(HOME_ASSISTANT) + len(HOME_ASSISTANT)] + '/'
SECRET_FILES_DIR = '{}secret_files/'.format(HASS_DIR)

load_dotenv('{}.env'.format(SECRET_FILES_DIR))

HASS_DB_URL = getenv('HASS_DB_URL')

con = connect(HASS_DB_URL)
cur = con.cursor()
cur.execute(f"SELECT pg_database_size('homeassistant');")

int(cur.fetchone()[0]) / 1024 ** 3
