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

RTP_TARGET_HOST = '127.0.0.1'
RTP_TARGET_PORT = 5005

def rtp_send_thread(sip_client):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print("Starting RTP transmission...")
    seq_num = 0
    ssrc = 98765
    
    try:
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
                udp_sock.sendto(packet, (RTP_TARGET_HOST, RTP_TARGET_PORT))
                
                seq_num = (seq_num + 1) % 65536
                
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"RTP Error: {e}")
    finally:
        udp_sock.close()
        print("RTP transmission stopped.")

def main():
    sip_client = SIPClient(port=5061)
    sip_client.start()
    
    print("Initiating call...")
    sip_client.call('127.0.0.1', 5060)
    
    # Wait for call to be established
    while sip_client.state != SIPState.IN_CALL:
        time.sleep(0.1)
        if sip_client.state == SIPState.ENDED:
            print("Call failed or was ended.")
            sip_client.stop()
            return
            
    # Call established, start media
    rtp_thread = threading.Thread(target=rtp_send_thread, args=(sip_client,))
    rtp_thread.start()
    
    try:
        print("Press Ctrl+C to end the call.")
        while sip_client.state == SIPState.IN_CALL:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nHanging up...")
        
    sip_client.hangup()
    time.sleep(1) # wait for BYE to be sent and ACK'd
    sip_client.stop()
    rtp_thread.join()

if __name__ == "__main__":
    main()
