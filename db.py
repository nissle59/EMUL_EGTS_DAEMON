import datetime
import logging

import psycopg2
from psycopg2.extras import RealDictCursor
import config

LOGGER = logging.getLogger(__name__)
conn = psycopg2.connect(
     database=config.DATABASE['database'],
     user=config.DATABASE['user'],
     password=config.DATABASE['password'],
     host=config.DATABASE['host'],
     port="5432",
     cursor_factory=RealDictCursor)

cur = conn.cursor()


def get_active_proxies(proxy_type: str = 'SOCKS5'):
    LOGGER = logging.getLogger(__name__+".get_active_proxies")
    if proxy_type == "HTTPS":
        view_name = 'public.https_active_proxies'
    elif proxy_type == 'SOCKS5':
        view_name = 'public.soocks_active_proxies'
    else:
        view_name = 'public.active_proxies'

    query = f"SELECT * FROM {view_name}"
    cur.execute(query)
    data = cur.fetchall()
    if data is None:
        return []

    return data


def get_proxy(proxy_id):
    LOGGER = logging.getLogger(__name__ + ".get_proxy")
    q = "SELECT * FROM public.proxies WHERE proxy_id = %(pid)s"
    cur.execute(q, {'pid': proxy_id})
    px = cur.fetchone()
    LOGGER.debug("%s: " + str(px), config.name)
    if px:
        http_str = f'http://{px.get("username","")}:{px.get("password","")}@{px.get("ip","")}:{px.get("port","")}'
        https_str = f'http://{px.get("username", "")}:{px.get("password", "")}@{px.get("ip", "")}:{px.get("port", "")}'
        proxy = {
            'http': http_str,
            'https': https_str
        }
        LOGGER.debug("%s: " + str(proxy), config.name)
        return proxy
    else:
        return None

