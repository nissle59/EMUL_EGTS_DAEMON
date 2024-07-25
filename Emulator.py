import errno
import json
import socket
import sys
import time
import traceback
from itertools import cycle
import logging
import pika
import requests
from pika.exceptions import AMQPConnectionError
import socks
import threading

from requests.auth import HTTPBasicAuth

import db
import model
# from db import Database as DB
from EGTStrack import EGTStrack as E
import config
from config import MQ

LOGGER = logging.getLogger(__name__)
imeis = []

proxies = db.get_active_proxies()
r_proxies = cycle(proxies)


def send_stop_signal(imei, task_id):
    LOGGER = logging.getLogger(__name__ + ".send_stop_signal")
    try:
        r = requests.get(
            url=f"http://api-external.tm.8525.ru/rnis/emulationCompleted?token=5jossnicxhn75lht7aimal7r2ocvg6o7&taskId={task_id}&imei={imei}",
            verify=False)
        LOGGER.info(f"[{r.status_code}] Sent stop signal for imei: {imei} with task {task_id}")
    except Exception as e:
        LOGGER.critical(e, exc_info=True)


def generate_imsi(imei):
    LOGGER = logging.getLogger(__name__ + ".generate_imsi")
    mcc = imei[:3]
    mnc = imei[3:5]
    msin = imei[-11:]
    imsi = mcc + mnc + msin
    return imsi


def generate_msisdn(imei):
    LOGGER = logging.getLogger(__name__ + ".generate_msisdn")
    country_code = imei[:2]
    ndc = imei[2:4]
    subscriber_number = imei[-11:]
    msisdn = country_code + ndc + subscriber_number
    return msisdn


class Emulator:
    def __init__(self, imei):
        self.stopped = False
        self.rhead = {
            'Content-Type': 'application/json'
        }
        LOGGER = logging.getLogger(__name__ + ".Emulator--init")
        # self.s_addr = '46.50.138.139'    # отправка в Форт
        # self.s_port = 65521              # отправка в Форт
        self.s_addr = 'data.rnis.mos.ru'  # отправка в РНИС
        self.s_port = 4444  # отправка в РНИС
        # self.s_addr = '127.0.0.1'
        # self.s_port = 7777
        self.imei = imei
        self.imsi = generate_imsi(imei)
        self.msisdn = generate_msisdn(imei)
        self.tid = None
        self.mq_connection = None
        LOGGER.info("%s: " + f"IMEI Length: {len(self.imei)}", config.name)
        # self.mq_channel.queue_declare(queue=str(imei), auto_delete=True)

        self.socket_connect()
        # sends a message to the server

    def socket_connect(self):
        LOGGER = logging.getLogger(__name__ + ".Emulator--socket_connect")
        while not self.stopped:
            try:
                prx = next(r_proxies)
                socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, prx['ip'], int(prx['port']), True, prx['username'],
                                      prx['password'])
                socket.socket = socks.socksocket
                self.sock = socket.socket()
                self.sock.connect((self.s_addr, self.s_port))
                self.egts_instance = E(deviceimei=self.imei, imsi=self.imsi, msisdn=self.msisdn)
                message_b = self.egts_instance.new_message()  # get message

                LOGGER.info("%s: " + '{} >> {}'.format(self.imei, message_b.hex()), config.name)
                try:
                    self.sock.sendall(message_b)  # sends a message to the server
                    recv_b = self.sock.recv(256)  #
                    LOGGER.info("%s: " + '{} >> {}'.format(self.s_addr, recv_b.hex()), config.name)
                    # self.i = 0
                    self.to_send = []
                except IOError as e:
                    if e.errno in [errno.EPIPE, errno.EBADF]:
                        # Обработка ошибки 'Broken pipe'
                        LOGGER.error("%s: " + 'Broken pipe or bad file decr error detected.', config.name,
                                     exc_info=True)
                        # Тут можно закрыть сокет и попытаться восстановить соединение
                        try:
                            self.sock.close()
                        except:
                            pass
                        time.sleep(1)
                        self.socket_connect()
                        self.sock.sendall(message_b)
                # sys.exit(0)
                break
            except Exception as e:
                LOGGER.error("%s: " + str(e), config.name, exc_info=True)
                time.sleep(1)

    def start(self):
        LOGGER = logging.getLogger(__name__ + ".Emulator--start")
        LOGGER.info("%s: " + ' [*] Waiting for messages. To exit press CTRL+C', config.name)
        self.consume_messages()

    def pause(self):
        LOGGER = logging.getLogger(__name__ + ".Emulator--pause")
        pass

    def stop(self):
        LOGGER = logging.getLogger(__name__ + ".Emulator--stop")
        try:
            self.sock.close()
        except Exception as e:
            LOGGER.debug("%s: " + str(e), config.name)

    def clear(self):
        LOGGER = logging.getLogger(__name__ + ".Emulator--clear")
        pass

    def prepare_message(self, point: model.Point):
        LOGGER = logging.getLogger(__name__ + ".Emulator--prepare_message")
        self.egts_instance.add_service(16,
                                       long=point.longitude,
                                       lat=point.latitude,
                                       speed=point.speed,
                                       angle=point.angle
                                       )
        message_b = self.egts_instance.new_message()
        return message_b

    def send(self, point):
        LOGGER = logging.getLogger(__name__ + ".Emulator--send")
        # message_b = self.prepare_message(point)
        message_b = point
        self.to_send.append(message_b)
        # LOGGER.info("%s: " + f"Angle: {point.angle} now: long[{point.longitude}] lat[{point.latitude}]", config.name)
        # LOGGER.info("%s: " + '{} : {} >> {}'.format(self.imei[-8:],self.imei,f'Data sent OK!'), config.name)
        try:
            list_len = len(self.to_send)
            for k in range(list_len):
                msg_b = self.to_send.pop(0)
                try:
                    self.sock.sendall(msg_b)  # sends a message to the server
                    LOGGER.info("%s: " + '{} : {} >> {} -- ({})'.format(self.imei[-8:], self.imei, f'Data sent OK!',
                                                                        str(msg_b.hex())), config.name)
                    try:
                        resp = self.sock.recv(256)
                        LOGGER.info("%s: " + '{} : {} >> {} -- ({})'.format(self.imei[-8:], self.imei, f'Data recved',
                                                                            str(resp.hex())), config.name)
                    except:
                        LOGGER.info("%s: " + '{} : {} >> {}'.format(self.imei[-8:], self.imei, f'Data NOT recved'),
                                    config.name)

                except Exception as e:
                    LOGGER.info("%s: " + '{} : {} >> {}'.format(self.imei[-8:], self.imei, f'### Data sent ERROR'),
                                config.name)
                    if e.errno in [errno.EPIPE, errno.EBADF]:
                        # Обработка ошибки 'Broken pipe'
                        LOGGER.error("%s: " + 'Broken pipe or bad file error detected.', config.name, exc_info=True)
                        # Тут можно закрыть сокет и попытаться восстановить соединение
                        try:
                            self.sock.close()
                        except:
                            pass
                        time.sleep(1)
                        self.socket_connect()
                        self.sock.sendall(msg_b)  # sends a message to the server
                # recv_b = self.sock.recv(256)
                # LOGGER.info("%s: " + '{} >> {}'.format(self.s_addr, f'Data received!'), config.name)
            # if list_len == 1:
            #     time.sleep(1)
        except Exception as e:
            LOGGER.error("%s: " + str(e), config.name, exc_info=True)
            # if self.mq_connection and not self.mq_connection.is_closed:
            #     self.mq_connection.close()
            # self.consume_messages()
        # self.i += 1

    def callback(self, ch, method, properties, body):
        LOGGER = logging.getLogger(__name__ + ".Emulator--callback")
        msg = int(0).to_bytes(64, byteorder='little')
        if body != msg:
            m = model.Point.from_b64(body)
            self.tid = m.tid
            self.send(m.to_egts_packet(self.egts_instance, self.imei, self.imsi, self.msisdn))
        else:
            LOGGER.info("%s: " + "!!!!!!!!!! EOF !!!!!!!!!!", config.name)
            self.stop_queue()

    def create_connection(self):
        LOGGER = logging.getLogger(__name__ + ".Emulator--create_connection")
        connection_params = pika.ConnectionParameters(
            host=MQ.host,
            port=MQ.port,
            virtual_host=f'{MQ.vhost}',
            credentials=pika.PlainCredentials(
                username=MQ.user,
                password=MQ.password
            )
        )
        return pika.BlockingConnection(connection_params)

    def create_channel(self, connection):
        LOGGER = logging.getLogger(__name__ + ".Emulator--create_channel")
        self.mq_channel = connection.channel()
        #self.mq_channel.queue_declare(queue=self.imei, auto_delete=False, durable=True, arguments={'x-expires': 120000})
        return self.mq_channel

    def start_consuming(self, channel):
        LOGGER = logging.getLogger(__name__ + ".Emulator--start_consuming")
        self.mq_channel.basic_consume(queue=self.imei, on_message_callback=self.callback, auto_ack=True,
                                      consumer_tag='EMUL_EGTS_DAEMON')
        self.mq_channel.start_consuming()

    def consume_messages(self):
        LOGGER = logging.getLogger(__name__ + ".Emulator--consume_messages")
        while True:
            try:
                defprx = socks.get_default_proxy()
                socks.setdefaultproxy(None)
                self.mq_connection = self.create_connection()
                self.mq_channel = self.create_channel(self.mq_connection)
                socks.setdefaultproxy(defprx)
                self.start_consuming(self.mq_channel)
            except AMQPConnectionError as e:
                # Можно реализовать здесь вашу логику логирования или отчетности
                LOGGER.info("%s: " + "Connection was closed, retrying...", config.name)
                time.sleep(5)  # Ждем перед повторной попыткой переподключения
            finally:
                if self.mq_connection:
                    if not self.mq_connection.is_closed:
                        self.mq_connection.close()

    def stop_queue(self):
        LOGGER = logging.getLogger(__name__ + ".Emulator--stop_queue")
        defprx = socks.get_default_proxy()
        socks.setdefaultproxy(None)
        self.stopped = True

        send_stop_signal(self.imei, self.tid)

        self.mq_channel.stop_consuming(consumer_tag='EMUL_EGTS_DAEMON')
        self.mq_channel.basic_cancel(consumer_tag='EMUL_EGTS_DAEMON')
        try:
            self.mq_channel.queue_delete(queue=f"{self.imei}_base")
            LOGGER.info(f'Queue deleted: {self.imei}_base')
        except:
            pass
        try:
            self.mq_channel.queue_delete(queue=self.imei)
            LOGGER.info(f'Queue deleted: {self.imei}')
        except:
            pass
        # try:
        #     r = requests.delete(
        #         url=f'http://{MQ.host}:{MQ.apiport}/api/exchanges/{MQ.vhost}/{self.imei}_ex',
        #         auth=HTTPBasicAuth(MQ.user, MQ.password),
        #         headers=self.rhead
        #     )
        #     LOGGER.info(f'Exchange deleted: {self.imei}_ex')
        # except:
        #     pass
        try:
            imeis.remove(self.imei)
        except:
            pass
        socks.setdefaultproxy(defprx)


def process_thread(imei):
    LOGGER = logging.getLogger(__name__ + ".process_thread")
    emul = Emulator(imei)
    LOGGER.info("%s: " + 'Connected', config.name)
    emul.start()


threads = {}


def add_imei(imei):
    LOGGER = logging.getLogger(__name__ + ".add_imei")
    if imei not in imeis:
        threads[imei] = threading.Thread(target=process_thread, args=(imei,), daemon=True)
        imeis.append(imei)
        threads[imei].start()
        LOGGER.info("%s: " + f'Started thread {imei} with seconds interval', config.name)


def queues_list():
    LOGGER = logging.getLogger(__name__ + ".queues_list")
    defprx = socks.get_default_proxy()
    socks.setdefaultproxy(None)
    r = requests.get(f"http://{MQ.host}:{MQ.apiport}/api/queues", auth=(MQ.user, MQ.password), verify=False,
                     proxies=None)
    socks.setdefaultproxy(defprx)
    js = r.json()
    # LOGGER.info("%s: " + js, config.name)
    queues = []
    q_list = [item.get('name', '') for item in js]
    for item in js:
        if item.get('vhost', None) == MQ.vhost:
            name = item.get('name')
            try:
                try:
                    imei = int(name)
                except:
                    pass
                if f"{imei}_base" in q_list:
                    queues.append(int(name))
                else:
                    try:
                        defprx = socks.get_default_proxy()
                        socks.setdefaultproxy(None)
                        r = requests.delete(f"http://{MQ.host}:{MQ.apiport}/api/queues/{MQ.vhost}/{imei}",
                                            auth=(MQ.user, MQ.password),
                                            verify=False, proxies=None)
                        socks.setdefaultproxy(defprx)
                    except Exception as e:
                        traceback.print_exc()
            except:
                pass
    queues = list(set(queues))
    return queues


def check_threads(queues):
    LOGGER = logging.getLogger(__name__ + ".check_threads")
    for imei in imeis:
        if not threads.get(imei, None):
            threads[imei] = threading.Thread(target=process_thread, args=(imei,), daemon=True)
            threads[imei].start()
            LOGGER.info("%s: " + f'Started thread {imei} with seconds interval', config.name)
    for thread in threads:
        if not (threads[thread].is_alive()):
            LOGGER.info("%s: " + f'Finished thread {thread}', config.name)
            try:
                imeis.remove(thread)
            except Exception as e:
                LOGGER.error("%s: " + str(e), config.name, exc_info=True)


if __name__ == '__main__':
    LOGGER = logging.getLogger(__name__)
    LOGGER.info("%s: " + "Starting Emulator", config.name)
    while True:
        LOGGER.debug(
            "%s: " + '------------------------------------\n  Scanning Threads...\n------------------------------------',
            config.name)
        time.sleep(3)
        qs = queues_list()
        check_threads(qs)
        for q in qs:
            if q not in imeis:
                add_imei(str(q))
