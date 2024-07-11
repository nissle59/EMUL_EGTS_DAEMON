import socket

import socks

from EGTStrack import EGTStrack

socket.socket = socks.socksocket

while True:
    try:
        sock = socket.socket()
        sock.connect(('data.rnis.mos.ru', 4444))   # отправка в РНИС
        #sock.connect(('46.50.138.139', 65521))     # отправка в Форт
        #sock.connect(('10.8.0.1', 6000))           # отправка на VPS
        #sock.connect(('127.0.0.1', 7777))          # отрравка в сниффер

        #cmd1 = EGTStrack(deviceid="40614705", deviceimei="358480081523995")
        egts_instance = EGTStrack(deviceimei="358480081523995")

        message_b = egts_instance.new_message()  # get message

        print('CLT >> "{}"'.format(message_b.hex()))
        sock.sendall(message_b)  # sends a message to the server
        recv_b = sock.recv(256)  #
        print('SRV >> "{}"'.format(recv_b.hex()))

        i = 0
        # for coord in coords:
        #     egts_instance.add_service(16,
        #                               long=coord['longitude'],
        #                               lat=coord['latitude'],
        #                               speed=coord['speed'],
        #                               angle=coord['angle']
        #                               )
        #     message_b = egts_instance.new_message()
        #     print(f"Angle: {coord['angle']} now: long[{coord['longitude']}] lat[{coord['latitude']}, next: long[{coord.get('next_coord',{}).get('longitude', None)}] lat[{coord.get('next_coord',{}).get('latitude', None)}]")
        #     print('CLT >> "{}"'.format(message_b.hex()))
        #     sock.sendall(message_b)
        #     recv_b = sock.recv(256)
        #     print('SRV >> "{}"'.format(recv_b.hex()))
        #     time.sleep(1)
        #     i += 1

        sock.close()


    except socket.timeout as msg:
        print("Timeouterror : %s" % msg)
        continue
    except socket.error as exc:
        print("Caught exception: %s" % exc)
        continue
    except TypeError as msg:
        print("Type Error : %s" % msg)
        continue
    except socks.GeneralProxyError as msg:
        print("GeneralProxyError : %s" % msg)
        continue
    finally:
        try:
            sock.close()
        except:
            pass
    #break