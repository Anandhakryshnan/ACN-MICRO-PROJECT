import tkinter as tk
from tkinter import messagebox
import socket
import threading
import subprocess
import sys
import os
import random
from receiver import start_receiver
from sender import start_sender
from p2p_session import start_p2p

# --- Dashboard Theme ---
BG = "#050505"
CARD = "#111111"
TEXT = "#FFFFFF"
MUTED = "#888888"
PRIMARY = "#333333"
PRIMARY_HOVER = "#555555"
ENTRY_BG = "#000000"

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
            width=20,  # REDUCED WIDTH for grid layout
            height=1   # REDUCED HEIGHT to fit more buttons on screen
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
        self.root.title("Spectra Voice - P2P Matrix")
        self.root.configure(bg=BG)
        # We removed the fixed geometry so Tkinter will auto-size the window to fit everything exactly.
        self.root.resizable(False, False)
        
        # Background Canvas for Animations
        self.canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        
        self.particles = []
        for _ in range(60):
            x = random.randint(0, 600)
            y = random.randint(0, 800)
            speed = random.uniform(0.5, 2.0)
            size = random.randint(1, 3)
            color = random.choice(["#222222", "#444444", "#666666"])
            item = self.canvas.create_oval(x, y, x+size, y+size, fill=color, outline="")
            self.particles.append([item, speed])
            
        self.animate_bg()
        
        try:
            self.local_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            self.local_ip = "127.0.0.1"
            
        self.stop_event = threading.Event()
        self.mute_event = threading.Event()
        self.setup_ui()
        
    def animate_bg(self):
        for p in self.particles:
            item, speed = p[0], p[1]
            self.canvas.move(item, 0, speed)
            pos = self.canvas.coords(item)
            if pos and pos[1] > 800:
                self.canvas.move(item, 0, -800 - random.randint(10, 50))
        self.root.after(30, self.animate_bg)
        
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", pady=(20, 10))
        tk.Label(header, text="SPECTRA VOICE", font=("Segoe UI Black", 24), bg=BG, fg="#FFFFFF").pack()
        tk.Label(header, text="Zero-Latency P2P Audio Matrix", font=("Segoe UI", 11), bg=BG, fg=MUTED).pack()
        
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
        self.status_label.pack(pady=(0, 5))
        
        self.packet_label = tk.Label(card, text="Packets Received: 0", font=("Segoe UI", 9, "bold"), bg=CARD, fg=MUTED)
        self.packet_label.pack(pady=(0, 20))
        
        # Buttons - Grid Layout
        btn_frame = tk.Frame(card, bg=CARD)
        btn_frame.pack(pady=10)
        
        self.btn_connect = DashboardButton(btn_frame, text="🚀 CONNECT", bg="#3B82F6", activebackground="#2563EB", command=self.start_connect)
        self.btn_connect.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="we")
        
        self.btn_mute = DashboardButton(btn_frame, text="🎤 MUTE", bg="#F59E0B", activebackground="#D97706", command=self.toggle_mute)
        self.btn_mute.grid(row=1, column=0, padx=5, pady=5, sticky="we")
        
        self.btn_end = DashboardButton(btn_frame, text="🛑 END CALL", bg="#EF4444", activebackground="#DC2626", command=self.end_call)
        self.btn_end.grid(row=1, column=1, padx=5, pady=5, sticky="we")
        
        self.btn_graph = DashboardButton(btn_frame, text="📊 DELAY GRAPH", bg="#8B5CF6", activebackground="#7C3AED", command=self.show_graph)
        self.btn_graph.grid(row=2, column=0, padx=5, pady=5, sticky="we")
        
        self.btn_jitter = DashboardButton(btn_frame, text="📉 JITTER GRAPH", bg="#EC4899", activebackground="#DB2777", command=self.show_jitter_graph)
        self.btn_jitter.grid(row=2, column=1, padx=5, pady=5, sticky="we")

    def update_status(self, status):
        status_map = {
            "Idle": ("● IDLE", MUTED),
            "Listening": ("● LISTENING...", TEXT),
            "Calling": ("● CALLING...", TEXT),
            "In-Call": ("● IN-CALL", TEXT)
        }
        text, color = status_map.get(status, (status, TEXT))
        try:
            if self.root.winfo_exists():
                self.root.after(0, lambda: self.status_label.config(text=text, fg=color))
        except Exception:
            pass

    def update_packets(self, count):
        try:
            if self.root.winfo_exists():
                self.root.after(0, lambda: self.packet_label.config(text=f"Packets Received: {count}", fg="#10B981" if count > 0 else MUTED))
        except Exception:
            pass

    def start_connect(self):
        target_ip = self.target_ip_entry.get().strip()
        if not target_ip:
            messagebox.showerror("Error", "Please enter a Target IP Address")
            return
            
        self.stop_event.clear()
        self.update_status("Connecting")
        self.btn_connect.config(state="disabled", bg=MUTED)
        self.update_packets(0)
        
        def run():
            try:
                start_p2p(target_ip, self.update_status, self.stop_event, self.mute_event, self.update_packets)
            except Exception as e:
                messagebox.showerror("Error", f"Connection failed:\n{e}")
                self.update_status("Idle")
            finally:
                self.btn_connect.config(state="normal", bg="#3B82F6")
                
        t = threading.Thread(target=run, daemon=True)
        t.start()

    def end_call(self):
        self.stop_event.set()

    def toggle_mute(self):
        if self.mute_event.is_set():
            self.mute_event.clear()
            self.btn_mute.config(text="🎤 MUTE", bg="#F59E0B", fg=TEXT)
        else:
            self.mute_event.set()
            self.btn_mute.config(text="🔇 UNMUTE", bg=TEXT, fg=BG)

    def show_graph(self):
        try:
            # If we have data, show the interactive matplotlib window
            if os.path.exists("jitter_metrics.csv") and os.path.getsize("jitter_metrics.csv") > 0:
                subprocess.Popen([sys.executable, "plot_metrics.py"])
            else:
                messagebox.showwarning("No Data", "No graph data found. Please make a call first.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not show graph: {e}")

    def show_jitter_graph(self):
        try:
            # If we have data, show the interactive matplotlib window
            if os.path.exists("jitter_metrics.csv") and os.path.getsize("jitter_metrics.csv") > 0:
                subprocess.Popen([sys.executable, "plot_jitter.py"])
            else:
                messagebox.showwarning("No Data", "No graph data found. Please make a call first.")
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
