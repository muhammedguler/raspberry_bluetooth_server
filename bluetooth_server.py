import os
import glob
import time
from bluetooth import *
import threading

class BluetoothServer:
    def __init__(self) -> None:
        self.connection = False
        self.server_sock = None
        self.client_sock = None
        self.port = None

        self.wifiname = None
        self.wifipassword = None
        self.ip = None
        



    def open_pair_mode(self):
        os.system("bluetoothctl discoverable on")
        os.system("sudo touch /home/pi/pins")
        f = open("/home/pi/pins", "w")
        f.write("* *")
        f.close()
        os.system("sudo bt-agent --capability=DisplayOnly -p /home/pi/pins")

    def start_server_sock_listenning(self):
        self.server_sock=BluetoothSocket( RFCOMM )
        self.server_sock.bind(("",PORT_ANY))
        self.server_sock.listen(1)
        self.port = self.server_sock.getsockname()[1]
        uuid = "7c7dfdc9-556c-4551-bb46-391b1dd27cc0"
        advertise_service( self.server_sock, "PiServer",
                        service_id = uuid,
                        service_classes = [ uuid, SERIAL_PORT_CLASS ],
                        profiles = [ SERIAL_PORT_PROFILE ] 
        #                   protocols = [ OBEX_UUID ] 
                            )
        
    def send_ip(self):
        time.sleep(15)
        self.ip = "Alınamadı"
        os.system("sudo rm -r ifconfig.txt")
        os.system("ifconfig > ifconfig.txt")
        file = open("/home/pi/Desktop/ifconfig.txt","r")
        lines = file.readlines()
        for line in lines:
            if "255.255.255" in line:
                lineArray = line.split("inet")
                lineArray = lineArray[1].split(" ")
                self.ip = lineArray[1]
                print(self.ip)
        self.client_sock.send(self.ip.encode())
        
    def waiting_connection(self):
        while True:
            self.wifiname = None
            self.wifipassword = None
            if(self.connection == False):
                print("Waiting for connection on RFCOMM channel %d" % self.port)
                self.client_sock, client_info = self.server_sock.accept()
                self.connection = True
                print("Accepted connection from ", client_info)
            try:
                print("Waiting for data receive...")
                data = self.client_sock.recv(1024)
                data = data.decode('utf-8')
                print("incoming data:", data)
                data = data.split()
                print(data)
                self.wifiname = data[0]
                self.wifipassword = data[1]
                #os.system("sudo rm -r /etc/wpa_supplicant/wpa_supplicant.conf")
                os.system("sudo touch /etc/wpa_supplicant/wpa_supplicant.conf")
                wpa = """ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{name}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
""".format(name = self.wifiname,password = self.wifipassword)
                f = open("/etc/wpa_supplicant/wpa_supplicant.conf", "w")
                f.write(wpa)
                f.close()
                os.system("wpa_cli -i wlan0 reconfigure")
                print("wifi name:",self.wifiname)
                print("wifi password:",self.wifipassword)
                threading.Thread(target=self.send_ip,daemon=True).start()
            except IOError:
                print("Connection disconnected!")
                self.client_sock.close()
                self.connection = False
            except BluetoothError:
                print("Something wrong with bluetooth")
                self.connection = False
            except KeyboardInterrupt:
                print("\nDisconnected")
                self.client_sock.close()
                self.server_sock.close()
                self.connection = False
                break


    def run(self):
        threading.Thread(target=self.open_pair_mode,daemon=True).start()
        time.sleep(3)
        os.system("sudo hciconfig hci piscan")
        self.connection = False
        self.start_server_sock_listenning()
        self.waiting_connection()
        

bluetoothServer = BluetoothServer()
bluetoothServer.run()
