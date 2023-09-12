import os
import glob
import time
from bluetooth import *
import threading
import netifaces
import cups
import json

class BluetoothServer:
    def __init__(self) -> None:
        self.connection = False
        self.server_sock = None
        self.client_sock = None
        self.port = None

        self.wifiname = None
        self.wifipassword = None
        self.ip = None
        self.WifiConnection = False
        self.printerStatus = None

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
        self.ip = None
        self.timeout = time.time()
        self.WifiConnection = True
        while((self.ip==None) and (self.WifiConnection) ):
            try:
                time.sleep(0.01)
                if((time.time()-self.timeout)>300):
                    self.WifiConnection = False  
                    break
                self.ip = netifaces.ifaddresses('wlan0')[netifaces.AF_INET][0]['addr']
            except:
                pass
        print(self.ip)  # should print "192.168.100.37"
        if(self.ip != None): # bağlantı kuruldu ise devam et
            self.SendJson = {'Command':'IP','Data':self.ip}
            self.client_sock.send(json.dumps(self.SendJson,indent=4).encode()) 
            self.SendJson = {'Command':'URL','Data':"http://" + self.ip + ":5000/"}# CP BOX mobilin bağlanacağı url 😹
            self.client_sock.send(json.dumps(self.SendJson,indent=4).encode())
            self.checkPrinter() #IP gönderilebiliyorsa yazıcı da gönderilebilir 
            self.check_DBYS_Connection() # IP gönderilebiliyorsa bağlantıyı kontrol edebilir

    def checkPrinter(self):
        conn = cups.Connection()
        self.printers = conn.getDefault()
        #self.printerStatus = printers #bağlı yazıcının adını yada None Döner
        self.printerStatus = False if self.printers == None else True #yazıcı bağlı ise True döner 
        self.SendJson = {'Command':'PRINTER','Data':{'isAvaible':self.printerStatus,'Name':self.printers}}
        self.client_sock.send(json.dumps(self.SendJson,indent=4).encode()) # gönderilecek mesaj düzenlenmeli

    def check_DBYS_Connection(self):
        self.DbysConnected = False
        self.hostName = "www.dnsins.com"
        response = os.system("ping -c 1 " + self.hostName)
        self.DbysConnected = True if response == 0 else False
        self.SendJson = {'Command':'DBYS_CONNECTION','Data':{'isAvaible':self.DbysConnected,'Name':self.hostName}}
        self.client_sock.send(json.dumps(self.SendJson,indent=4).encode()) # gönderilecek mesaj düzenlenmeli
        
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
                self.WifiConnection = False
                self.startTime = time.time()
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
                if((time.time()-self.startTime)<0.05):
                    time.sleep((0.05-(time.time()-self.startTime)))
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
