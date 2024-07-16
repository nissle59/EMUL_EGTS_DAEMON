import json
import logging.config
import logging.handlers
import socket

import socks


class NoProxyHTTPHandler(logging.handlers.HTTPHandler):
    def emit(self, record):
        # Сохраняем текущие настройки прокси
        current_proxy = socks.get_default_proxy()

        # Отключаем прокси для текущего потока
        socks.setdefaultproxy(None)
        socket.socket = socks.socksocket

        try:
            # Отправляем лог без использования прокси
            super().emit(record)
        finally:
            # Восстанавливаем настройки прокси
            if current_proxy:
                socks.setdefaultproxy(current_proxy.proxy_type, current_proxy.addr, current_proxy.port,
                                      current_proxy.rdns, current_proxy.username, current_proxy.password)
                socket.socket = socks.socksocket
            else:
                socks.setdefaultproxy(None)
                socket.socket = socks.socksocket

name = "EGTS Emulator (Virtual GPS Devices)"

logging.config.dictConfig(json.load(open('logging.json','r')))
LOGGER = logging.getLogger(__name__)

class MQ:
    host = 'rmq.db.services.local'
    #host = '10.8.0.5'
    user = 'rmuser'
    password = 'rmpassword'
    port = 5672
    apiport = 15672
    vhost = 'egts'

DATABASE = {
    'host': 'pg.db.services.local',
    #'host': '10.8.0.5',
    'user': 'postgres',
    'password': 'psqlpass',
    'database': 'vindcgibdd'
}

# logging.basicConfig(level=logging.INFO)
#
# handler = logging.FileHandler('app.log')
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# s_handler = logging.StreamHandler(sys.stdout)
# logger = logging.getLogger(__name__)
# logger.addHandler(handler)
# logger.addHandler(s_handler)
# logger.setLevel(logging.INFO)
# logging.getLogger("pika").setLevel(logging.CRITICAL)
# logging.getLogger("requests").setLevel(logging.CRITICAL)
# logger.propagate = False