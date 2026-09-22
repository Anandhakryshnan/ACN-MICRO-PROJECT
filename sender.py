"""
sender.py
Handles capturing audio from the microphone and sending it over RTP/UDP.
"""

import socket
import threading
import time
import sounddevice as sd
import zlib

from sip_signaling import SIPClient, SIPState
from rtp_helper import create_rtp_packet

# --- Configuration ---
CHUNK = 160  # 20ms of audio at 8000Hz
FORMAT = 'int16'
CHANNELS = 1
RATE = 8000

def rtp_send_thread(sip_client, target_ip, stop_event=None, mute_event=None):
    """
    Captures raw audio from the microphone and transmits it to the target IP via RTP/UDP.
    """
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq_num = 0
    ssrc = 98765

    try:
        with sd.RawInputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=CHUNK, latency='low') as stream:
            while sip_client.state == SIPState.IN_CALL and not (stop_event and stop_event.is_set()):
                # Read audio data
                payload, _ = stream.read(CHUNK)
                if mute_event and mute_event.is_set():
                    payload_bytes = b'\x00' * CHUNK * 2
                else:
                    payload_bytes = bytes(payload)

                # Compress payload
                payload_bytes = zlib.compress(payload_bytes)

                # Precise millisecond wall-clock timestamp
                timestamp_ms = int(time.time() * 1000)

                # Pack timestamp into 32 bits (lower 32 bits)
                timestamp_32 = timestamp_ms & 0xFFFFFFFF

                packet = create_rtp_packet(seq_num, timestamp_32, payload_bytes, ssrc)
                udp_sock.sendto(packet, (target_ip, 5005))

                seq_num = (seq_num + 1) % 65536

    except KeyboardInterrupt:
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"RTP Error: {e}")
    finally:
        udp_sock.close()
        print("RTP transmission stopped.")

def start_sender(target_ip='127.0.0.1', status_callback=None, stop_event=None, mute_event=None):
    """
    Initializes the SIP client, calls the target, and starts the RTP transmission thread.
    """
    sip_client = SIPClient(host='0.0.0.0', port=5061)
    sip_client.start()

    print(f"Initiating call to {target_ip}...")
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
            sip_client.stop()
            if status_callback:
                status_callback("Idle")
            return

    print("Call established!")
    if status_callback:
        status_callback("In-Call")

    print(f"Starting RTP transmission to {target_ip}...")
    # pylint: disable=line-too-long
    rtp_thread = threading.Thread(target=rtp_send_thread, args=(sip_client, target_ip, stop_event, mute_event), daemon=True)
    rtp_thread.start()

    from receiver import rtp_recv_thread, playout_thread, AdaptiveJitterBuffer
    import csv
    f = open('jitter_metrics.csv', 'w', newline='', buffering=1)
    writer = csv.writer(f)
    writer.writerow(['seq_num', 'send_time', 'recv_time', 'transit_delay', 'moving_delay', 'jitter', 'playout_target'])
    
    jitter_buffer = AdaptiveJitterBuffer()
    recv_thread = threading.Thread(target=rtp_recv_thread, args=(sip_client, jitter_buffer, writer), daemon=True)
    play_thread = threading.Thread(target=playout_thread, args=(sip_client, jitter_buffer), daemon=True)
    
    recv_thread.start()
    play_thread.start()

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
    f.close()
    if status_callback:
        status_callback("Idle")
