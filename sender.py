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
from audio_config import CHUNK, FORMAT, CHANNELS, RATE

def rtp_send_thread(sip_client, target_ip, stop_event=None, mute_event=None, udp_sock=None):
    """
    Captures raw audio from the microphone and transmits it to the target IP via RTP/UDP.
    """
    own_sock = False
    if udp_sock is None:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        own_sock = True
    seq_num = 0
    ssrc = 98765

    try:
        # Removed latency='low' to allow OS to pick a safe buffer size, fixing Realtek crash issues
        with sd.RawInputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=CHUNK) as stream:
            while sip_client.state == SIPState.IN_CALL and not (stop_event and stop_event.is_set()):
                try:
                    # Read audio data
                    payload, _ = stream.read(CHUNK)
                    if mute_event and mute_event.is_set():
                        payload_bytes = b'\x00' * CHUNK * 2
                    else:
                        payload_bytes = bytes(payload)
                except Exception as e:
                    # If microphone fails (e.g. privacy settings, no device), send silence instead of dying
                    print(f"Microphone read error: {e}")
                    payload_bytes = b'\x00' * CHUNK * 2

                # Compress payload
                payload_bytes = zlib.compress(payload_bytes)

                # Precise millisecond wall-clock timestamp
                timestamp_ms = int(time.time() * 1000)

                # Pack timestamp into 32 bits (lower 32 bits)
                timestamp_32 = timestamp_ms & 0xFFFFFFFF

                packet = create_rtp_packet(seq_num, timestamp_32, payload_bytes, ssrc)
                try:
                    udp_sock.sendto(packet, (target_ip, 5005))
                except Exception as e:
                    # Ignore transient network errors like WinError 10054 (ICMP Port Unreachable)
                    pass

                seq_num = (seq_num + 1) % 65536

    except KeyboardInterrupt:
        pass
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"RTP Error: {e}")
    finally:
        if own_sock:
            udp_sock.close()
        print("RTP transmission stopped.")
