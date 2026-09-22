import threading
import time
import socket
import csv
from sip_signaling import SIPServer, SIPClient, SIPState
from receiver import rtp_recv_thread, playout_thread, AdaptiveJitterBuffer
from sender import rtp_send_thread

def start_p2p(target_ip, status_callback=None, stop_event=None, mute_event=None, packet_callback=None):
    """
    Symmetrically negotiates a P2P call by listening on 5060 and actively calling target_ip:5060.
    """
    # Start SIP Server to listen for incoming calls
    sip_server = SIPServer(host='0.0.0.0', port=5060)
    sip_server.start()

    # Start SIP Client to actively call the target
    sip_client = SIPClient(host='0.0.0.0', port=5061)
    sip_client.start()

    # We use a background thread to repeatedly send INVITEs
    def caller_thread():
        sip_client.call(target_ip, 5060)
    
    c_thread = threading.Thread(target=caller_thread, daemon=True)
    c_thread.start()

    print(f"Negotiating symmetric connection with {target_ip}...")
    
    # Wait until either the Server receives a call OR the Client establishes a call
    active_sip = None
    while not (stop_event and stop_event.is_set()):
        if sip_server.state == SIPState.IN_CALL:
            active_sip = sip_server
            print("Connection established as Receiver!")
            # We received a call. Stop our client from trying to call them.
            sip_client.stop()
            break
        elif sip_client.state == SIPState.IN_CALL:
            active_sip = sip_client
            print("Connection established as Caller!")
            # We successfully called them. Stop our server from accepting new calls.
            sip_server.stop()
            break
        
        # Check if the client failed to connect after all retries
        if sip_client.state == SIPState.ENDED:
            # Client failed, restart it so it keeps trying until the user clicks End Call
            sip_client.state = SIPState.IDLE
            threading.Thread(target=caller_thread, daemon=True).start()
            
        time.sleep(0.1)

    # If the user clicked "End Call" before connection was established
    if not active_sip or (stop_event and stop_event.is_set()):
        sip_server.stop()
        sip_client.stop()
        if status_callback:
            status_callback("Idle")
        return

    if status_callback:
        status_callback("In-Call")

    jitter_buffer = AdaptiveJitterBuffer()

    with open('jitter_metrics.csv', 'w', newline='', buffering=1) as f:
        writer = csv.writer(f)
        writer.writerow(['seq_num', 'send_time', 'recv_time', 'transit_delay', 'moving_delay', 'jitter', 'playout_target'])
        
        # Start RTP Threads
        recv_thread = threading.Thread(target=rtp_recv_thread, args=(active_sip, jitter_buffer, writer), daemon=True)
        recv_thread.start()
        
        # If we are the Server, the caller's IP is in active_sip.client_address[0]
        # If we are the Client, the target IP is target_ip
        remote_ip = active_sip.client_address[0] if active_sip == sip_server else target_ip
        
        rtp_thread = threading.Thread(target=rtp_send_thread, args=(active_sip, remote_ip, stop_event, mute_event), daemon=True)
        rtp_thread.start()
        
        playout = threading.Thread(target=playout_thread, args=(active_sip, jitter_buffer), daemon=True)
        playout.start()
        
        try:
            print("Press Ctrl+C or use UI to end the call.")
            while active_sip.state == SIPState.IN_CALL:
                if stop_event and stop_event.is_set():
                    break
                if packet_callback:
                    packet_callback(jitter_buffer.total_packets)
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    print("\nHanging up...")
    
    # Send BYE message to gracefully end the call on the other side
    active_sip.hangup()
    
    # Give it a second to send the packet
    time.sleep(1)
        
    active_sip.stop()
    if status_callback:
        status_callback("Idle")
