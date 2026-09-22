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
import zlib

from sip_signaling import SIPServer, SIPState
from rtp_helper import unpack_rtp_packet
from jitter_buffer import AdaptiveJitterBuffer
from audio_config import CHUNK, FORMAT, CHANNELS, RATE

def rtp_recv_thread(sip_server, jitter_buffer, writer, udp_sock=None):
    """
    Listens for incoming RTP packets on UDP port 5005, unpacks them, 
    and pushes them into the adaptive jitter buffer.
    """
    own_sock = False
    if udp_sock is None:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_sock.bind(('0.0.0.0', 5005))
        udp_sock.settimeout(1.0)
        own_sock = True
    
    print("Listening for RTP packets...")

    try:
        while sip_server.state == SIPState.IN_CALL:
            try:
                packet, _ = udp_sock.recvfrom(2048)
                seq_num, send_time_32, payload = unpack_rtp_packet(packet)
                
                try:
                    payload = zlib.decompress(payload)
                except zlib.error:
                    continue # Skip corrupted packets
                
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
        if own_sock:
            udp_sock.close()
        print("RTP receiving stopped.")

def playout_thread(sip_server, jitter_buffer):
    """
    Pulls 20ms audio frames from the jitter buffer and writes them to the audio output stream.
    """
    import numpy as np
    print("Starting audio playout...")
    
    try:
        # Removed latency='low' to let the OS negotiate a safe buffer, fixing audio driver crashes
        with sd.RawOutputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=CHUNK) as stream:
            while sip_server.state == SIPState.IN_CALL:
                # Pop 20ms of audio from jitter buffer
                audio_data = jitter_buffer.pop()
                
                # Apply 4x digital gain to boost quiet microphones
                samples = np.frombuffer(audio_data, dtype=np.int16)
                # Use int32 to prevent overflow during multiplication, then clip and cast back
                amplified = np.clip(samples.astype(np.int32) * 4, -32768, 32767).astype(np.int16)
                
                stream.write(amplified.tobytes())
                
    except Exception as e:  # pylint: disable=broad-exception-caught
        if "Stream is stopped" not in str(e):
            print(f"Playout Error: {e}")
