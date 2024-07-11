import errno
import json
import socket
import sys
import time
from itertools import cycle

import pika
import requests
from pika.exceptions import AMQPConnectionError
import socks
import threading

import db
import model
# from db import Database as DB
from EGTStrack import EGTStrack as E
import config
from config import MQ

imeis = []

proxies = db.get_active_proxies()
r_proxies = cycle(proxies)
# from ApiService import ApiService as API


def generate_imsi(imei):
    # MCC (Mobile Country Code) - используем первые 3 цифры IMEI
    mcc = imei[:3]
    # MNC (Mobile Network Code) - используем следующие 2 цифры IMEI
    mnc = imei[3:5]
    # MSIN (Mobile Subscriber Identification Number) - случайные оставшиеся 11 цифр
    msin = imei[-11:]
    imsi = mcc + mnc + msin
    return imsi
    #return '1111111111111111'


def generate_msisdn(imei):
    # Country Code - используем первые 2 цифры IMEI
    country_code = imei[:2]
    # National Destination Code (NDC) - используем следующие 2 цифры IMEI
    ndc = imei[2:4]
    # Subscriber Number - случайные оставшиеся цифры до нужной длины (8)
    subscriber_number = imei[-11:]
    msisdn = country_code + ndc + subscriber_number
    return msisdn
    #return '111111111111111'


class Emulator:
    def __init__(self, imei):
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
        config.logger.info(f"IMEI Length: {len(self.imei)}")
        #self.mq_channel.queue_declare(queue=str(imei), auto_delete=True)

        self.socket_connect()
          # sends a message to the server


    def socket_connect(self):
        while True:
            try:
                prx = next(r_proxies)
                socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, prx['ip'], int(prx['port']), True, prx['username'], prx['password'])
                socket.socket = socks.socksocket
                self.sock = socket.socket()
                self.sock.connect((self.s_addr, self.s_port))
                self.egts_instance = E(deviceimei=self.imei, imsi=self.imsi, msisdn=self.msisdn)
                message_b = self.egts_instance.new_message()  # get message

                config.logger.info('{} >> {}'.format(self.imei, message_b.hex()))
                try:
                    self.sock.sendall(message_b)  # sends a message to the server
                    recv_b = self.sock.recv(256)  #
                    config.logger.info('{} >> {}'.format(self.s_addr, recv_b.hex()))
                    # self.i = 0
                    self.to_send = []
                except IOError as e:
                    if e.errno in [errno.EPIPE, errno.EBADF]:
                        # Обработка ошибки 'Broken pipe'
                        config.logger.info('Broken pipe or bad file decr error detected.')
                        # Тут можно закрыть сокет и попытаться восстановить соединение
                        try:
                            self.sock.close()
                        except:
                            pass
                        time.sleep(1)
                        self.socket_connect()
                        self.sock.sendall(message_b)
                #sys.exit(0)
                break
            except Exception as e:
                config.logger.info(e)
                time.sleep(1)


    def start(self):
        config.logger.info(' [*] Waiting for messages. To exit press CTRL+C')
        self.consume_messages()


    def pause(self):
        pass

    def stop(self):
        try:
            self.sock.close()
        except Exception as e:
            config.logger.info(e)

    def clear(self):
        pass

    def prepare_message(self, point: model.Point):
        self.egts_instance.add_service(16,
                                       long=point.longitude,
                                       lat=point.latitude,
                                       speed=point.speed,
                                       angle=point.angle
                                       )
        message_b = self.egts_instance.new_message()
        return message_b

    def send(self, point):
        #message_b = self.prepare_message(point)
        message_b = point
        self.to_send.append(message_b)
        #config.logger.info(f"Angle: {point.angle} now: long[{point.longitude}] lat[{point.latitude}]")
        #config.logger.info('{} : {} >> {}'.format(self.imei[-8:],self.imei,f'Data sent OK!'))
        try:
            list_len = len(self.to_send)
            for k in range(list_len):
                msg_b = self.to_send.pop(0)
                try:
                    self.sock.sendall(msg_b)  # sends a message to the server
                    config.logger.info('{} : {} >> {} -- ({})'.format(self.imei[-8:],self.imei,f'Data sent OK!', str(msg_b.hex())))
                    try:
                        resp = self.sock.recv(256)
                        config.logger.info('{} : {} >> {} -- ({})'.format(self.imei[-8:], self.imei, f'Data recved', str(resp.hex())))
                    except:
                        config.logger.info('{} : {} >> {}'.format(self.imei[-8:], self.imei, f'Data NOT recved'))

                except Exception as e:
                    config.logger.info('{} : {} >> {}'.format(self.imei[-8:], self.imei, f'### Data sent ERROR'))
                    if e.errno in [errno.EPIPE, errno.EBADF]:
                        # Обработка ошибки 'Broken pipe'
                        config.logger.info('Broken pipe or bad file error detected.')
                        # Тут можно закрыть сокет и попытаться восстановить соединение
                        try:
                            self.sock.close()
                        except: pass
                        time.sleep(1)
                        self.socket_connect()
                        self.sock.sendall(msg_b)  # sends a message to the server
                #recv_b = self.sock.recv(256)
                #config.logger.info('{} >> {}'.format(self.s_addr, f'Data received!'))
            # if list_len == 1:
            #     time.sleep(1)
        except Exception as e:
            config.logger.info(e)
            # if self.mq_connection and not self.mq_connection.is_closed:
            #     self.mq_connection.close()
            # self.consume_messages()
        # self.i += 1

    def callback(self, ch, method, properties, body):
        #config.logger.info(f" [x] Received {body}")
        #p = model.Point.from_json_b(body)
        #msg = b'0000000000000000000000000000000000000000000000000000000000000000'
        msg = int(0).to_bytes(64, byteorder='little')
        if body != msg:
            m = model.Point.from_b64(body)
            self.tid = m.tid
            # self.egts_instance.add_service(1)
            # message_b = self.egts_instance.new_message()
            # config.logger.info('{} >> {}'.format(self.imei, message_b.hex()))
            # self.sock.sendall(message_b)  # sends a message to the server
            # recv_b = self.sock.recv(256)  #
            # config.logger.info('{} >> {}'.format(self.s_addr, recv_b.hex()))
            self.send(m.to_egts_packet(self.egts_instance ,self.imei, self.imsi, self.msisdn))
        else:
            config.logger.info("!!!!!!!!!! EOF !!!!!!!!!!")
            self.stop_queue()

    def create_connection(self):
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
        self.mq_channel = connection.channel()
        self.mq_channel.queue_declare(queue=self.imei, auto_delete=False, durable=True)
        return self.mq_channel

    def start_consuming(self, channel):
        self.mq_channel.basic_consume(queue=self.imei, on_message_callback=self.callback, auto_ack=True, consumer_tag='EMUL_EGTS_DAEMON')
        self.mq_channel.start_consuming()

    def consume_messages(self):
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
                config.logger.info("Connection was closed, retrying...")
                time.sleep(5)  # Ждем перед повторной попыткой переподключения
            finally:
                if self.mq_connection:
                    if not self.mq_connection.is_closed:
                        self.mq_connection.close()

    def stop_queue(self):
        defprx = socks.get_default_proxy()
        socks.setdefaultproxy(None)
        r = requests.get(
            f"http://api-external.tm.8525.ru/rnis/emulationCompleted?token=5jossnicxhn75lht7aimal7r2ocvg6o7&taskId={self.tid}&imei={self.imei}",
            verify=False)
        self.mq_channel.stop_consuming(consumer_tag='EMUL_EGTS_DAEMON')
        self.mq_channel.basic_cancel(consumer_tag='EMUL_EGTS_DAEMON')
        try:
            self.mq_channel.queue_delete(queue=f"{self.imei}_base")
        except:
            pass
        try:
            self.mq_channel.queue_delete(queue=self.imei)
        except:
            pass
        config.logger.info(f'Queue deleted: {self.imei}')
        try:
            imeis.remove(self.imei)
        except:
            pass
        socks.setdefaultproxy(defprx)


def process_thread(imei):
    emul = Emulator(imei)
    config.logger.info('Connected')
    emul.start()

threads = {}

def add_imei(imei):
    if imei not in imeis:
        threads[imei] = threading.Thread(target=process_thread, args=(imei,), daemon=True)
        imeis.append(imei)
        threads[imei].start()
        config.logger.info(f'Started thread {imei} with seconds interval')


def queues_list():
    defprx = socks.get_default_proxy()
    socks.setdefaultproxy(None)
    r = requests.get(f"http://{MQ.host}:{MQ.apiport}/api/queues", auth=(MQ.user, MQ.password), verify=False, proxies=None)
    socks.setdefaultproxy(defprx)
    js = r.json()
    #config.logger.info(js)
    queues = []
    for item in js:
        if item.get('vhost', None) == MQ.vhost:
            name = item.get('name')
            try:
                queues.append(int(name))
            except:
                pass
    return queues

def check_threads():
    for imei in imeis:
        if not threads.get(imei, None):
            threads[imei] = threading.Thread(target=process_thread, args=(imei,), daemon=True)
            threads[imei].start()
            config.logger.info(f'Started thread {imei} with seconds interval')
    for thread in threads:
        if not(threads[thread].is_alive()):
            config.logger.info(f'Finished thread {thread}')
            try:
                imeis.remove(thread)
            except Exception as e:
                config.logger.info(e)

if __name__ == '__main__':
    while True:
        config.logger.info('------------------------------------\n  Scanning Threads...\n------------------------------------')
        time.sleep(3)
        qs = queues_list()
        check_threads()
        for q in qs:
            if q not in imeis:
                add_imei(str(q))
