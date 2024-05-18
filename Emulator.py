import json
import socket
import time
import pika
import requests
from pika.exceptions import AMQPConnectionError
import socks
import threading
import model
# from db import Database as DB
from EGTStrack import EGTStrack as E
from config import MQ

imeis = []

# from ApiService import ApiService as API


class Emulator:
    def __init__(self, imei):
        # self.s_addr = '46.50.138.139'    # отправка в Форт
        # self.s_port = 65521              # отправка в Форт
        self.s_addr = 'data.rnis.mos.ru'  # отправка в РНИС
        self.s_port = 4444  # отправка в РНИС
        self.imei = imei
        #self.mq_channel.queue_declare(queue=str(imei), auto_delete=True)
        socket.socket = socks.socksocket
        self.sock = socket.socket()
        while True:
            try:
                self.sock.connect((self.s_addr, self.s_port))
                break
            except Exception as e:
                print(e)
        if len(self.imei) < 10:
            self.egts_instance = E(deviceimei=imei, deviceid=imei)
        else:
            self.egts_instance = E(deviceimei=imei)
        message_b = self.egts_instance.new_message()  # get message

        print('{} >> {}'.format(self.imei, message_b.hex()))
        self.sock.sendall(message_b)  # sends a message to the server
        recv_b = self.sock.recv(256)  #
        print('{} >> {}'.format(self.s_addr, recv_b.hex()))
        # self.i = 0
        self.to_send = []


    def start(self):
        print(' [*] Waiting for messages. To exit press CTRL+C')
        self.consume_messages()


    def pause(self):
        pass

    def stop(self):
        try:
            self.sock.close()
        except Exception as e:
            print(e)

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
        #print(f"Angle: {point.angle} now: long[{point.longitude}] lat[{point.latitude}]")
        print('{} >> {}'.format(self.imei,f'Data sent OK!'))
        try:
            list_len = len(self.to_send)
            for k in range(list_len):
                msg_b = self.to_send.pop(0)
                self.sock.sendall(msg_b)
                recv_b = self.sock.recv(256)
                print('{} >> {}'.format(self.s_addr, f'Data received!'))
            # if list_len == 1:
            #     time.sleep(1)
        except Exception as e:
            print(e)
            # if self.mq_connection and not self.mq_connection.is_closed:
            #     self.mq_connection.close()
            # self.consume_messages()
        # self.i += 1

    def callback(self, ch, method, properties, body):
        #print(f" [x] Received {body}")
        #p = model.Point.from_json_b(body)
        msg = b'0000000000000000000000000000000000000000000000000000000000000000'
        if body != msg:
            self.send(body)
        else:
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
        self.mq_channel.queue_declare(queue=self.imei, auto_delete=False)
        return self.mq_channel

    def start_consuming(self, channel):
        self.mq_channel.basic_consume(queue=self.imei, on_message_callback=self.callback, auto_ack=True, consumer_tag='EMUL_EGTS_DAEMON')
        self.mq_channel.start_consuming()

    def consume_messages(self):
        while True:
            try:
                self.mq_connection = self.create_connection()
                self.mq_channel = self.create_channel(self.mq_connection)
                self.start_consuming(self.mq_channel)
            except AMQPConnectionError as e:
                # Можно реализовать здесь вашу логику логирования или отчетности
                print("Connection was closed, retrying...")
                time.sleep(5)  # Ждем перед повторной попыткой переподключения
            finally:
                if self.mq_connection and not self.mq_connection.is_closed:
                    self.mq_connection.close()

    def stop_queue(self):
        self.mq_channel.stop_consuming(consumer_tag='EMUL_EGTS_DAEMON')
        self.mq_channel.queue_delete(queue=self.imei, if_empty=True)
        try:
            imeis.remove(self.imei)
        except:
            pass


def process_thread(imei):
    emul = Emulator(imei)
    print('Connected')
    emul.start()

threads = {}

def add_imei(imei):
    if imei not in imeis:
        threads[imei] = threading.Thread(target=process_thread, args=(imei,), daemon=True)
        imeis.append(imei)
        threads[imei].start()
        print(f'Started thread {imei} with seconds interval')
        # thread.join()
        # print(f'Finished thread {imei}')
        # try:
        #     imeis.remove(imei)
        # except:
        #     pass

def queues_list():
    r = requests.get(f"http://{MQ.host}:{MQ.apiport}/api/queues", auth=(MQ.user, MQ.password), verify=False)
    js = r.json()
    #print(js)
    queues = []
    for item in js:
        if item.get('vhost', None) == MQ.vhost:
            queues.append(item.get('name'))
    return queues

def check_threads():
    for thread in threads:
        if not(threads[thread].is_alive()):
            print(f'Finished thread {thread}')
            try:
                imeis.remove(thread)
            except:
                pass

if __name__ == '__main__':
    q = '44294049'
    add_imei(q)
    # while True:
    #     qs = queues_list()
    #     check_threads()
    #     for q in qs:
    #         if q not in imeis:
    #             add_imei(q)
