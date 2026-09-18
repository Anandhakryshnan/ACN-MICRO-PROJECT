"""
receiver.py
Handles receiving RTP audio packets over UDP, passing them to a jitter buffer,
and playing them out through the speakers.
"""

import socket
import threading
import time
import csv
import sounddevice as sd

from sip_signaling import SIPServer, SIPState
from rtp_helper import unpack_rtp_packet
from jitter_buffer import AdaptiveJitterBuffer

# --- Configuration ---
CHUNK = 160  # 20ms of audio at 8000Hz
FORMAT = 'int16'
CHANNELS = 1
RATE = 8000

def rtp_recv_thread(sip_server, jitter_buffer, writer):
    """
    Listens for incoming RTP packets on UDP port 5005, unpacks them, 
    and pushes them into the adaptive jitter buffer.
    """
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_sock.bind(('0.0.0.0', 5005))
    udp_sock.settimeout(1.0)
    
    print("Listening for RTP packets...")

    try:
        while sip_server.state == SIPState.IN_CALL:
            try:
                packet, _ = udp_sock.recvfrom(2048)
                seq_num, send_time_32, payload = unpack_rtp_packet(packet)
                
                # Push to jitter buffer
                jitter_buffer.push(seq_num, send_time_32, payload)
                
                # Retrieve and log stats
                stats = jitter_buffer.get_stats()
                if stats and writer:
                    writer.writerow([
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
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"RTP Recv Error: {e}")
    finally:
        udp_sock.close()
        print("RTP receiving stopped.")

def playout_thread(sip_server, jitter_buffer):
    """
    Pulls 20ms audio frames from the jitter buffer and writes them to the audio output stream.
    """
    print("Starting audio playout...")
    
    try:
        with sd.RawOutputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=CHUNK) as stream:
            while sip_server.state == SIPState.IN_CALL:
                # Pop 20ms of audio from jitter buffer
                audio_data = jitter_buffer.pop()
                
                # stream.write is blocking, ensuring correct timing
                stream.write(audio_data)
                
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Playout Error: {e}")

def start_receiver(status_callback=None, stop_event=None):
    """
    Initializes the SIP server, waits for an incoming call, 
    and starts the RTP receiving and playout threads.
    """
    # Setup CSV file for metrics using 'with' to satisfy pylint, but since it spans threads,
    # we manage it explicitly and suppress the R1732 warning.
    # pylint: disable=consider-using-with,unspecified-encoding
    f = open('jitter_metrics.csv', 'w', newline='', buffering=1)
    writer = csv.writer(f)
    writer.writerow(['seq_num', 'send_time', 'recv_time', 'transit_delay', 'moving_delay', 'jitter', 'playout_target'])
    
    sip_server = SIPServer(host='0.0.0.0', port=5060)
    sip_server.start()
    
    jitter_buffer = AdaptiveJitterBuffer()
    
    # Wait for a call to be established
    while sip_server.state != SIPState.IN_CALL:
        if stop_event and stop_event.is_set():
            sip_server.stop()
            f.close()
            if status_callback:
                status_callback("Idle")
            return
        time.sleep(0.1)
        
    print("Call accepted! Starting media processing...")
    if status_callback:
        status_callback("In-Call")
        
    # pylint: disable=line-too-long
    recv_thread = threading.Thread(target=rtp_recv_thread, args=(sip_server, jitter_buffer, writer), daemon=True)
    play_thread = threading.Thread(target=playout_thread, args=(sip_server, jitter_buffer), daemon=True)
    
    recv_thread.start()
    play_thread.start()
    
    try:
        while sip_server.state == SIPState.IN_CALL:
            if stop_event and stop_event.is_set():
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
        
    print("\nEnding call...")
    sip_server.state = SIPState.ENDED
        
    time.sleep(1)
    sip_server.stop()
    f.close()
    print("Receiver shut down cleanly.")
    if status_callback:
        status_callback("Idle")
