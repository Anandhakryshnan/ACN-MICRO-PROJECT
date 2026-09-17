import sounddevice as sd
import socket
import threading
import time
import csv
from sip_signaling import SIPServer, SIPState
from rtp_helper import unpack_rtp_packet
from jitter_buffer import AdaptiveJitterBuffer

CHANNELS = 1
RATE = 8000
CHUNK = 160

RTP_LISTEN_HOST = '127.0.0.1'
RTP_LISTEN_PORT = 5005

def get_full_timestamp(rtp_ts_32):
    """
    Reconstruct full 64-bit millisecond timestamp from the 32-bit RTP timestamp.
    Assumes sender and receiver have synchronized clocks (e.g., localhost testing).
    """
    local_time_ms = int(time.time() * 1000)
    high_32 = local_time_ms & 0xFFFFFFFF00000000
    full_ts = high_32 | rtp_ts_32
    
    # Handle wrap-around near boundaries
    if full_ts > local_time_ms + 2000000000:
        full_ts -= 0x100000000
    elif full_ts < local_time_ms - 2000000000:
        full_ts += 0x100000000
        
    return full_ts

def rtp_recv_thread(sip_server, jitter_buffer, metrics_file):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((RTP_LISTEN_HOST, RTP_LISTEN_PORT))
    udp_sock.settimeout(0.5)
    
    print("Listening for RTP packets...")
    
    try:
        while sip_server.state == SIPState.IN_CALL:
            try:
                data, addr = udp_sock.recvfrom(2048)
                seq_num, timestamp_32, payload = unpack_rtp_packet(data)
                
                # Reconstruct the 64-bit millisecond timestamp
                send_time_ms = get_full_timestamp(timestamp_32)
                
                jitter_buffer.push(seq_num, send_time_ms, payload)
                
                # Log metrics to CSV
                stats = jitter_buffer.get_stats()
                if stats:
                    metrics_file.writerow([
                        stats['seq_num'], 
                        stats['send_time'], 
                        stats['recv_time'],
                        stats['transit_delay'], 
                        stats['moving_delay'], 
                        stats['jitter'], 
                        stats['playout_target']
                    ])
            except socket.timeout:
                continue
    except Exception as e:
        print(f"RTP Recv Error: {e}")
    finally:
        udp_sock.close()

def playout_thread(sip_server, jitter_buffer):
    print("Starting audio playout...")
    
    try:
        with sd.RawOutputStream(samplerate=RATE, channels=CHANNELS, dtype='int16', blocksize=CHUNK) as stream:
            while sip_server.state == SIPState.IN_CALL:
                # Pop 20ms of audio from jitter buffer
                audio_data = jitter_buffer.pop()
                
                # stream.write is blocking, ensuring correct timing
                stream.write(audio_data)
                
    except Exception as e:
        print(f"Playout Error: {e}")

def main():
    # Setup CSV file for metrics
    f = open('jitter_metrics.csv', 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(['seq_num', 'send_time', 'recv_time', 'transit_delay', 'moving_delay', 'jitter', 'playout_target'])
    
    sip_server = SIPServer(port=5060)
    sip_server.start()
    
    jitter_buffer = AdaptiveJitterBuffer()
    
    print("Waiting for incoming calls on port 5060...")
    
    # Wait for a call to be established
    while sip_server.state != SIPState.IN_CALL:
        time.sleep(0.1)
        
    print("Call accepted! Starting media processing...")
    
    # Using threading.Lock inside csv writing isn't strictly necessary since only one thread writes, 
    # but the file object itself isn't fully thread-safe in Python if multiple threads wrote. Here it's fine.
    recv_thread = threading.Thread(target=rtp_recv_thread, args=(sip_server, jitter_buffer, writer))
    play_thread = threading.Thread(target=playout_thread, args=(sip_server, jitter_buffer))
    
    recv_thread.start()
    play_thread.start()
    
    try:
        while sip_server.state == SIPState.IN_CALL:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEnding call...")
        sip_server.state = SIPState.ENDED
        
    time.sleep(1)
    sip_server.stop()
    recv_thread.join()
    play_thread.join()
    f.close()
    print("Receiver shut down cleanly.")

if __name__ == "__main__":
    main()
