"""
test_system.py
Comprehensive diagnostic suite to test VoIP Engine subsystems.
"""

import sys
import os
import subprocess
import time
import csv

def print_header(title):
    """Prints a formatted header."""
    print("=" * 60)
    print(title)
    print("=" * 60)

def test_imports():
    """Tests if all required standard and third-party modules can be imported."""
    try:
        # pylint: disable=import-outside-toplevel,unused-import
        import sounddevice as sd
        import pandas as pd
        import matplotlib
        import tkinter
        import socket
        import struct
        import queue
        print(f"[PASS] Module Imports       {' ' * 20}")
        return True
    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"[FAIL] Module Imports       {e}")
        return False

def test_audio():
    """Tests if the sounddevice library can access audio hardware."""
    try:
        # pylint: disable=import-outside-toplevel
        import sounddevice as sd
        
        try:
            sd.query_devices(kind='input')
            sd.query_devices(kind='output')
            print("[PASS] Audio Subsystem      sounddevice initialized successfully")
            return True
        except Exception as ex: # pylint: disable=broad-exception-caught
            print(f"[FAIL] Audio Subsystem      {ex}")
            return False
            
    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"[FAIL] Audio Subsystem      {e}")
        return False

def test_sockets():
    """Tests if the required UDP ports (5060, 5005) can be bound."""
    try:
        # pylint: disable=import-outside-toplevel
        import socket
        
        sock_sip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_sip.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_sip.bind(('0.0.0.0', 5060))
        
        sock_rtp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_rtp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_rtp.bind(('0.0.0.0', 5005))
        
        sock_sip.close()
        sock_rtp.close()
        
        print("[PASS] Network Sockets      Ports 5060 and 5005 bound successfully")
        return True
    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"[FAIL] Network Sockets      {e}")
        return False

def test_math():
    """Tests Ramjee's algorithm variables in the jitter buffer."""
    try:
        # pylint: disable=import-outside-toplevel
        from jitter_buffer import AdaptiveJitterBuffer
        
        jb = AdaptiveJitterBuffer()
        # simulate packets
        jb.push(1, 1000, b"data")
        time.sleep(0.01)
        jb.push(2, 1020, b"data")
        
        stats = jb.get_stats()
        if stats and stats['jitter'] is not None:
            print("[PASS] Algorithm Math       Ramjee's algorithm variables computed")
            return True
        print("[FAIL] Algorithm Math       Variables returned None")
        return False
    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"[FAIL] Algorithm Math       {e}")
        return False

def test_pipeline():
    """Tests if CSV data can be written and plotted without errors."""
    try:
        # Create dummy CSV
        # pylint: disable=unspecified-encoding
        with open('jitter_metrics.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['seq_num', 'send_time', 'recv_time', 'transit_delay', 'moving_delay', 'jitter', 'playout_target'])
            writer.writerow([1, 1000, 1010, 10, 10, 0, 10])
            writer.writerow([2, 1020, 1035, 15, 12.5, 2.5, 22.5])
            
        # Run plot_metrics.py headlessly
        result = subprocess.run([sys.executable, "plot_metrics.py"], capture_output=True, text=True, check=False)
        
        if os.path.exists("jitter_analysis.png"):
            print("[PASS] Data Pipeline        jitter_analysis.png generated successfully")
            return True
        print(f"[FAIL] Data Pipeline        Image not generated. {result.stderr}")
        return False
    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"[FAIL] Data Pipeline        {e}")
        return False

def main():
    """Runs all tests and reports the result."""
    print_header("VoIP Engine - Comprehensive System Diagnostics")
    
    results = []
    results.append(test_imports())
    results.append(test_audio())
    results.append(test_sockets())
    results.append(test_math())
    results.append(test_pipeline())
    
    print("-" * 60)
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"Diagnostics complete. {passed}/{total} subsystems passed.\n")
    
    if passed == total:
        print("SUCCESS: All VoIP engine components are verified and operational.")
    else:
        print("WARNING: Some components failed. Check the logs above.")

if __name__ == "__main__":
    main()
