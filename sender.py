import sounddevice as sd
import socket
import time
import threading
from sip_signaling import SIPClient, SIPState
from rtp_helper import create_rtp_packet

# Audio configuration
CHANNELS = 1
RATE = 8000
CHUNK = 160  # 160 samples = 20ms of audio at 8000Hz

def rtp_send_thread(sip_client, target_ip):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Starting RTP transmission to {target_ip}...")
    seq_num = 0
    ssrc = 98765
    
    try:
        import sounddevice as sd
        with sd.RawInputStream(samplerate=RATE, channels=CHANNELS, dtype='int16', blocksize=CHUNK) as stream:
            while sip_client.state == SIPState.IN_CALL:
                # Read audio data
                payload, overflowed = stream.read(CHUNK)
                payload_bytes = bytes(payload)
                
                # Precise millisecond wall-clock timestamp
                timestamp_ms = int(time.time() * 1000)
                
                # Pack timestamp into 32 bits (lower 32 bits)
                timestamp_32 = timestamp_ms & 0xFFFFFFFF
                
                packet = create_rtp_packet(seq_num, timestamp_32, payload_bytes, ssrc)
                udp_sock.sendto(packet, (target_ip, 5005))
                
                seq_num = (seq_num + 1) % 65536
                
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"RTP Error: {e}")
    finally:
        udp_sock.close()
        print("RTP transmission stopped.")

def start_sender(target_ip='127.0.0.1', status_callback=None, stop_event=None):
    sip_client = SIPClient(host='0.0.0.0', port=5061)
    sip_client.start()
    
    print(f"Initiating call to {target_ip}...")
    if status_callback:
        status_callback("Calling")
        
    sip_client.call(target_ip, 5060)
    
    # Wait for call to be established
    while sip_client.state != SIPState.IN_CALL:
        if stop_event and stop_event.is_set():
            sip_client.stop()
            if status_callback:
                status_callback("Idle")
            return
        time.sleep(0.1)
        if sip_client.state == SIPState.ENDED:
            print("Call failed or was ended.")
            if status_callback:
                status_callback("Idle")
            sip_client.stop()
            return
            
    if status_callback:
        status_callback("In-Call")
            
    # Call established, start media
    rtp_thread = threading.Thread(target=rtp_send_thread, args=(sip_client, target_ip))
    rtp_thread.start()
    
    try:
        print("Press Ctrl+C or use UI to end the call.")
        while sip_client.state == SIPState.IN_CALL:
            if stop_event and stop_event.is_set():
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
        
    print("\nHanging up...")
    sip_client.state = SIPState.ENDED
        
    sip_client.hangup()
    time.sleep(1) # wait for BYE to be sent and ACK'd
    sip_client.stop()
    rtp_thread.join()
    
    if status_callback:
        status_callback("Idle")

if __name__ == "__main__":
    import sys
    ip = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    start_sender(ip)
