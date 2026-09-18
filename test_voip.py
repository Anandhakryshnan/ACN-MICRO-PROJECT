"""
test_voip.py
Comprehensive diagnostic suite to test VoIP Engine subsystems.
"""

import sys
import os
import subprocess
import time
import csv
import threading

def print_header(title):
    print("=" * 60)
    print(title)
    print("=" * 60)

def test_imports():
    try:
        import sounddevice as sd
        import pandas as pd
        import matplotlib
        import tkinter
        import socket
        import struct
        import queue
        print(f"[PASS] Module Imports       {' ' * 20}")
        return True
    except Exception as e:
        print(f"[FAIL] Module Imports       {e}")
        return False

def test_audio():
    try:
        import sounddevice as sd
        sd.query_devices(kind='input')
        sd.query_devices(kind='output')
        print("[PASS] Audio Subsystem      sounddevice initialized successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Audio Subsystem      {e}")
        return False

def test_sockets():
    try:
        import socket
        sock_sip_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_sip_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_sip_s.bind(('0.0.0.0', 5060))
        
        sock_sip_c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_sip_c.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_sip_c.bind(('0.0.0.0', 5061))
        
        sock_rtp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_rtp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_rtp.bind(('0.0.0.0', 5005))
        
        sock_sip_s.close()
        sock_sip_c.close()
        sock_rtp.close()
        
        print("[PASS] Network Sockets      Ports 5060, 5061 and 5005 bound successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Network Sockets      {e}")
        return False

def test_jitter_buffer_plc():
    try:
        from jitter_buffer import AdaptiveJitterBuffer
        jb = AdaptiveJitterBuffer()
        
        # 1. Push a normal packet
        payload_1 = b'\x11' * 320
        jb.push(1, 1000, payload_1)
        
        # Pop it
        popped_1 = jb.pop()
        if popped_1 != payload_1:
            print("[FAIL] Jitter Buffer PLC    Normal pop mismatch")
            return False
            
        # 2. Buffer is now empty. A pop should trigger PLC (50% attenuation)
        plc_payload = jb.pop()
        import struct
        expected_samples = struct.unpack(f'{320//2}h', payload_1)
        expected_attenuated = [int(s * 0.5) for s in expected_samples]
        expected_plc = struct.pack(f'{len(expected_attenuated)}h', *expected_attenuated)
        
        if plc_payload != expected_plc:
            print("[FAIL] Jitter Buffer PLC    PLC attenuation failed")
            return False
            
        print("[PASS] Jitter Buffer PLC    PLC attenuation logic working correctly")
        return True
    except Exception as e:
        print(f"[FAIL] Jitter Buffer PLC    {e}")
        return False

def test_pipeline():
    try:
        with open('jitter_metrics.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['seq_num', 'send_time', 'recv_time', 'transit_delay', 'moving_delay', 'jitter', 'playout_target'])
            writer.writerow([1, 1000, 1010, 10, 10, 0, 10])
            writer.writerow([2, 1020, 1035, 15, 12.5, 2.5, 22.5])
            
        result1 = subprocess.run([sys.executable, "plot_metrics.py"], capture_output=True, text=True, check=False)
        result2 = subprocess.run([sys.executable, "plot_jitter.py"], capture_output=True, text=True, check=False)
        
        if os.path.exists("jitter_analysis.png") and os.path.exists("jitter_variance.png"):
            print("[PASS] Data Pipeline        Graphs generated successfully")
            return True
        print(f"[FAIL] Data Pipeline        Images not generated.")
        return False
    except Exception as e:
        print(f"[FAIL] Data Pipeline        {e}")
        return False

def main():
    print_header("VoIP Engine - Comprehensive System Diagnostics")
    
    results = [
        test_imports(),
        test_audio(),
        test_sockets(),
        test_jitter_buffer_plc(),
        test_pipeline()
    ]
    
    print("-" * 60)
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Diagnostics complete. {passed}/{total} subsystems passed.\n")
    
    if passed == total:
        print("SUCCESS: All VoIP engine components are verified and operational.")
        sys.exit(0)
    else:
        print("WARNING: Some components failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
