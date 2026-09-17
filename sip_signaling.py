import socket
import threading
import time

class SIPState:
    IDLE = "IDLE"
    CALLING = "CALLING"
    IN_CALL = "IN_CALL"
    ENDED = "ENDED"

class SIPNode:
    def __init__(self, host='127.0.0.1', port=5060):
        self.host = host
        self.port = port
        self.state = SIPState.IDLE
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.running = False
        
    def send_message(self, target_host, target_port, message):
        try:
            self.sock.sendto(message.encode('ascii'), (target_host, target_port))
        except Exception as e:
            print(f"Error sending SIP message: {e}")

class SIPServer(SIPNode):
    def __init__(self, host='127.0.0.1', port=5060):
        super().__init__(host, port)
        self.client_address = None
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen)
        self.thread.daemon = True
        self.thread.start()
        
    def _listen(self):
        print(f"SIP Server listening on {self.host}:{self.port}")
        self.sock.settimeout(1.0)
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                if data:
                    self._handle_message(data.decode('ascii'), addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"SIP Server error: {e}")
                    
    def _handle_message(self, msg, addr):
        print(f"SIP Server received: {msg} from {addr}")
        self.client_address = addr
        
        if msg == "INVITE":
            self.state = SIPState.CALLING
            time.sleep(0.2) # Simulate processing
            self.send_message(addr[0], addr[1], "200 OK")
        elif msg == "ACK":
            self.state = SIPState.IN_CALL
            print("Call established!")
        elif msg == "BYE":
            self.state = SIPState.ENDED
            self.send_message(addr[0], addr[1], "200 OK")
            print("Call ended.")
            
    def stop(self):
        self.running = False
        self.sock.close()

class SIPClient(SIPNode):
    def __init__(self, host='127.0.0.1', port=5061):
        super().__init__(host, port)
        self.target_address = None
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen)
        self.thread.daemon = True
        self.thread.start()
        
    def _listen(self):
        print(f"SIP Client listening on {self.host}:{self.port}")
        self.sock.settimeout(1.0)
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                if data:
                    self._handle_message(data.decode('ascii'), addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"SIP Client error: {e}")
                    
    def _handle_message(self, msg, addr):
        print(f"SIP Client received: {msg} from {addr}")
        if msg == "200 OK" and self.state == SIPState.CALLING:
            self.state = SIPState.IN_CALL
            self.send_message(self.target_address[0], self.target_address[1], "ACK")
            print("Call established!")
        elif msg == "200 OK" and self.state == SIPState.ENDED:
            print("Call gracefully ended.")
            
    def call(self, target_host, target_port=5060):
        self.target_address = (target_host, target_port)
        self.state = SIPState.CALLING
        self.send_message(target_host, target_port, "INVITE")
        
    def hangup(self):
        if self.state == SIPState.IN_CALL and self.target_address:
            self.state = SIPState.ENDED
            self.send_message(self.target_address[0], self.target_address[1], "BYE")
            
    def stop(self):
        self.running = False
        self.sock.close()
