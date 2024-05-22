import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
import config


conn = psycopg2.connect(
     database=config.DATABASE['database'],
     user=config.DATABASE['user'],
     password=config.DATABASE['password'],
     host=config.DATABASE['host'],
     port="5432",
     cursor_factory=RealDictCursor)

cur = conn.cursor()


# def disable_proxy(proxy_id):
#     config.logger.debug(f'Disable {proxy_id} proxy')
#     sql = "UPDATE gosuslugi.proxies_map SET active = false WHERE id = %(pid)s"
#     cur.execute(sql, {'pid':proxy_id})
#     sql = "UPDATE gosuslugi.gu_accounts SET proxy_id = null WHERE proxy_id = %(pid)s"
#     cur.execute(sql, {'pid': proxy_id})
#     conn.commit()

# def set_proxy_for_account(account_id):
#     query = f"""UPDATE gosuslugi.gu_accounts SET proxy_id = (select proxy_id from gosuslugi.free_proxies limit 1) where account_id = %(account_id)s RETURNING proxy_id"""
#     cur.execute(query, {'account_id':account_id})
#     conn.commit()
#     data = cur.fetchone()
#     config.logger.debug(data)
#     if data:
#         try:
#             return int(dict(data)['proxy_id'])
#         except Exception as e:
#             config.logger.debug(f"set_proxy_err: {e}")
#     else:
#         return False



def get_active_proxies(proxy_type: str = 'SOCKS5'):
    if proxy_type == "HTTPS":
        view_name = 'public.https_active_proxies'
    elif proxy_type == 'SOCKS5':
        view_name = 'public.socks_active_proxies'
    else:
        view_name = 'public.active_proxies'

    query = "SELECT * FROM %(view_name)s"
    cur.execute(query, {'view_name':view_name})
    data = cur.fetchall()
    if data is None:
        return []

    return data


def get_proxy(proxy_id):
    q = "SELECT * FROM public.proxies WHERE proxy_id = %(pid)s"
    cur.execute(q, {'pid': proxy_id})
    px = cur.fetchone()
    #config.logger.debug(px)
    if px:
        http_str = f'http://{px.get("username",'')}:{px.get("password",'')}@{px.get("ip",'')}:{px.get("port",'')}'
        https_str = f'http://{px.get("username", '')}:{px.get("password", '')}@{px.get("ip", '')}:{px.get("port", '')}'
        proxy = {
            'http': http_str,
            'https': https_str
        }
        #config.logger.debug(proxy)
        return proxy
    else:
        return None

