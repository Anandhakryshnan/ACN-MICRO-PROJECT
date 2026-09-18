import tkinter as tk
from tkinter import messagebox
import socket
import threading
import subprocess
import sys
import os
from receiver import start_receiver
from sender import start_sender

# --- Dashboard Theme ---
BG = "#0f172a"
CARD = "#1e293b"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
PRIMARY = "#3b82f6"
PRIMARY_HOVER = "#2563eb"
ENTRY_BG = "#0f172a"

class DashboardButton(tk.Button):
    def __init__(self, master, **kw):
        self.default_bg = kw.pop('bg', PRIMARY)
        self.hover_bg = kw.pop('activebackground', PRIMARY_HOVER)
        
        tk.Button.__init__(self, master=master, **kw)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        self.configure(
            font=("Segoe UI", 10, "bold"),
            bg=self.default_bg,
            fg=TEXT,
            relief="flat",
            activebackground=self.hover_bg,
            activeforeground=TEXT,
            cursor="hand2",
            width=35,  # FIXED WIDTH FOR ALL BUTTONS
            height=2   # FIXED HEIGHT FOR ALL BUTTONS
        )
        
    def on_enter(self, e):
        if self['state'] != 'disabled':
            self['background'] = self.hover_bg

    def on_leave(self, e):
        if self['state'] != 'disabled':
            self['background'] = self.default_bg

class VoIPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VoIP Engine Dashboard")
        self.root.geometry("450x750")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        
        try:
            self.local_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            self.local_ip = "127.0.0.1"
            
        self.stop_event = threading.Event()
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", pady=(20, 10))
        tk.Label(header, text="VoIP ENGINE", font=("Segoe UI Black", 22), bg=BG, fg=TEXT).pack()
        tk.Label(header, text="Unified Communication Dashboard", font=("Segoe UI", 10), bg=BG, fg=PRIMARY).pack()
        
        # Card Container
        card = tk.Frame(self.root, bg=CARD, bd=0)
        card.pack(pady=10, padx=30, fill="both", expand=True)
        
        # Info Section
        tk.Label(card, text="LOCAL IP ADDRESS", font=("Segoe UI", 9, "bold"), bg=CARD, fg=MUTED).pack(pady=(20, 2))
        tk.Label(card, text=self.local_ip, font=("Consolas", 15), bg=CARD, fg=TEXT).pack(pady=(0, 15))
        
        tk.Label(card, text="TARGET IP ADDRESS", font=("Segoe UI", 9, "bold"), bg=CARD, fg=MUTED).pack(pady=(0, 2))
        
        entry_frame = tk.Frame(card, bg=MUTED, padx=1, pady=1)
        entry_frame.pack(pady=(0, 15))
        self.target_ip_entry = tk.Entry(entry_frame, font=("Consolas", 14), bg=ENTRY_BG, fg=TEXT, relief="flat", justify="center", insertbackground=TEXT, width=18)
        self.target_ip_entry.insert(0, self.local_ip)
        self.target_ip_entry.pack(ipady=4)
        
        tk.Label(card, text="CALL STATUS", font=("Segoe UI", 9, "bold"), bg=CARD, fg=MUTED).pack(pady=(0, 2))
        self.status_label = tk.Label(card, text="● IDLE", font=("Segoe UI", 12, "bold"), bg=CARD, fg=MUTED)
        self.status_label.pack(pady=(0, 20))
        
        # Buttons - All perfectly equal size
        btn_frame = tk.Frame(card, bg=CARD)
        btn_frame.pack()
        
        self.btn_listen = DashboardButton(btn_frame, text="🎧 LISTEN (RECEIVER)", command=self.start_listen)
        self.btn_listen.pack(pady=5)
        
        self.btn_call = DashboardButton(btn_frame, text="📞 CALL TARGET (SENDER)", command=self.start_call)
        self.btn_call.pack(pady=5)
        
        self.btn_end = DashboardButton(btn_frame, text="🛑 END CALL", bg="#ef4444", activebackground="#dc2626", command=self.end_call)
        self.btn_end.pack(pady=5)
        
        self.btn_graph = DashboardButton(btn_frame, text="📊 SHOW DELAY GRAPH", bg="#10b981", activebackground="#059669", command=self.show_graph)
        self.btn_graph.pack(pady=5)
        
        self.btn_jitter = DashboardButton(btn_frame, text="📉 SHOW JITTER VARIANCE", bg="#8b5cf6", activebackground="#7c3aed", command=self.show_jitter_graph)
        self.btn_jitter.pack(pady=5)
        
        self.btn_csv = DashboardButton(btn_frame, text="📄 OPEN RAW DATA (CSV)", bg="#64748b", activebackground="#475569", command=self.show_csv)
        self.btn_csv.pack(pady=5)

    def update_status(self, status):
        status_map = {
            "Idle": ("● IDLE", MUTED),
            "Listening": ("● LISTENING...", "#f59e0b"),
            "Calling": ("● CALLING...", "#f59e0b"),
            "In-Call": ("● IN-CALL", "#10b981")
        }
        text, color = status_map.get(status, (status, TEXT))
        try:
            if self.root.winfo_exists():
                self.root.after(0, lambda: self.status_label.config(text=text, fg=color))
        except Exception:
            pass

    def start_listen(self):
        self.stop_event.clear()
        self.update_status("Listening")
        self.btn_listen.config(state="disabled", bg="#475569")
        
        def run():
            try:
                start_receiver(self.update_status, self.stop_event)
            except Exception as e:
                messagebox.showerror("Error", f"Receiver failed to start:\n{e}")
                self.update_status("Idle")
            finally:
                self.btn_listen.config(state="normal", bg=PRIMARY)
                
        t = threading.Thread(target=run, daemon=True)
        t.start()

    def start_call(self):
        target_ip = self.target_ip_entry.get().strip()
        if not target_ip:
            messagebox.showerror("Error", "Please enter a Target IP Address")
            return
        
        self.stop_event.clear()
        self.update_status("Calling")
        self.btn_call.config(state="disabled", bg="#475569")
        
        def run():
            try:
                start_sender(target_ip, self.update_status, self.stop_event)
            except Exception as e:
                messagebox.showerror("Error", f"Sender failed to start:\n{e}")
                self.update_status("Idle")
            finally:
                self.btn_call.config(state="normal", bg=PRIMARY)
                
        t = threading.Thread(target=run, daemon=True)
        t.start()

    def end_call(self):
        self.stop_event.set()

    def show_graph(self):
        try:
            # If we have data, update the image silently
            if os.path.exists("jitter_metrics.csv") and os.path.getsize("jitter_metrics.csv") > 0:
                subprocess.run([sys.executable, "plot_metrics.py"], check=False)
                
            # Now show the image
            if os.path.exists("jitter_analysis.png"):
                os.startfile("jitter_analysis.png")
            else:
                messagebox.showwarning("No Image", "No graph image found. Please make a call first.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not show graph: {e}")

    def show_jitter_graph(self):
        try:
            # If we have data, update the image silently
            if os.path.exists("jitter_metrics.csv") and os.path.getsize("jitter_metrics.csv") > 0:
                subprocess.run([sys.executable, "plot_jitter.py"], check=False)
                
            # Now show the image
            if os.path.exists("jitter_variance.png"):
                os.startfile("jitter_variance.png")
            else:
                messagebox.showwarning("No Image", "No graph image found. Please make a call first.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not show jitter graph: {e}")

    def show_csv(self):
        if not os.path.exists("jitter_metrics.csv"):
            messagebox.showwarning("No Data", "Please make a call first to generate data.")
            return
        try:
            os.startfile("jitter_metrics.csv")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open CSV file: {e}")

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    app = VoIPApp(root)
    root.mainloop()
