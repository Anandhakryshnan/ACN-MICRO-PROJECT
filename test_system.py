import sys
import os
import subprocess
import time
import csv

def print_result(name, passed, detail=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status:6} {name:20} {detail}")
    return passed

def test_imports():
    try:
        import sounddevice as sd
        import pandas as pd
        import matplotlib
        import tkinter
        import socket
        import struct
        import queue
        return print_result("Module Imports", True)
    except ImportError as e:
        return print_result("Module Imports", False, str(e))

def test_audio():
    try:
        import sounddevice as sd
        try:
            # Check default devices
            in_info = sd.query_devices(kind='input')
            out_info = sd.query_devices(kind='output')
            return print_result("Audio Subsystem", True, "sounddevice initialized successfully")
        except Exception as e:
            return print_result("Audio Subsystem", False, f"Device error: {e}")
    except Exception as e:
        return print_result("Audio Subsystem", False, str(e))

def test_network():
    try:
        import socket
        sock_sip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_sip.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_sip.bind(('0.0.0.0', 5060))
        
        sock_rtp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_rtp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock_rtp.bind(('0.0.0.0', 5005))
        
        sock_sip.close()
        sock_rtp.close()
        return print_result("Network Sockets", True, "Ports 5060 and 5005 bound successfully")
    except Exception as e:
        return print_result("Network Sockets", False, str(e))

def test_math():
    try:
        from jitter_buffer import AdaptiveJitterBuffer
        jb = AdaptiveJitterBuffer(alpha=0.125, beta=0.125, K=4)
        
        # Simulated packets
        now = time.time() * 1000
        jb.push(1, now - 50, b'data1') # Transit delay = ~50
        jb.push(2, now - 60, b'data2') # Transit delay = ~60
        
        stats = jb.get_stats()
        if stats and 'moving_delay' in stats and 'jitter' in stats and 'playout_target' in stats:
            return print_result("Algorithm Math", True, "Ramjee's algorithm variables computed")
        else:
            return print_result("Algorithm Math", False, f"Missing statistics: {stats}")
    except Exception as e:
        return print_result("Algorithm Math", False, str(e))

def test_pipeline():
    try:
        f = open('jitter_metrics.csv', 'w', newline='', buffering=1)
        writer = csv.writer(f)
        writer.writerow(['seq_num', 'send_time', 'recv_time', 'transit_delay', 'moving_delay', 'jitter', 'playout_target'])
        
        for i in range(50):
            writer.writerow([i, 1000+i, 1050+i, 50, 50.0, 1.0, 54.0])
        f.close()
        
        # Remove old image to prove generation
        if os.path.exists("jitter_analysis.png"):
            os.remove("jitter_analysis.png")
            
        # Run plot_metrics.py
        res = subprocess.run([sys.executable, "plot_metrics.py"], capture_output=True, text=True)
        
        if os.path.exists("jitter_analysis.png"):
            return print_result("Data Pipeline", True, "jitter_analysis.png generated successfully")
        else:
            return print_result("Data Pipeline", False, f"Image not found. Error: {res.stderr}")
    except Exception as e:
        return print_result("Data Pipeline", False, str(e))

def main():
    print("=" * 60)
    print("VoIP Engine - Comprehensive System Diagnostics")
    print("=" * 60)
    
    passed = 0
    total = 5
    
    passed += 1 if test_imports() else 0
    passed += 1 if test_audio() else 0
    passed += 1 if test_network() else 0
    passed += 1 if test_math() else 0
    passed += 1 if test_pipeline() else 0
    
    print("-" * 60)
    print(f"Diagnostics complete. {passed}/{total} subsystems passed.")
    if passed == total:
        print("\nSUCCESS: All VoIP engine components are verified and operational.")
        sys.exit(0)
    else:
        print("\nFAILURE: One or more subsystems failed. See details above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
