import logging
import sys


class MQ:
    host = 'rmq.local'
    #host = '10.8.0.5'
    user = 'rmuser'
    password = 'rmpassword'
    port = 5672
    apiport = 15672
    vhost = 'egts'

DATABASE = {
    #'host': 'db.local',
    'host': '10.8.0.5',
    'user': 'postgres',
    'password': 'psqlpass',
    'database': 'vindcgibdd'
}

logging.basicConfig(level=logging.INFO)

handler = logging.FileHandler('app.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
s_handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.addHandler(s_handler)
logger.setLevel(logging.INFO)
logger.propagate = False