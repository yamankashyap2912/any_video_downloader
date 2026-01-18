import customtkinter as ctk
from tkinter import filedialog, messagebox
import yt_dlp
import threading
import os
import vlc
import platform
import time
from PIL import Image
import urllib.request
from io import BytesIO

class DownloadTask(ctk.CTkFrame):
    def __init__(self, master, filename, pause_callback, cancel_callback):
        super().__init__(master, fg_color="#34495e", corner_radius=10)
        self.pack(fill="x", pady=5, padx=5)
        self.is_paused = False
        self.is_cancelled = False
        self.filename = filename

        self.label = ctk.CTkLabel(self, text=filename, font=("Arial", 11, "bold"), anchor="w")
        self.label.pack(fill="x", padx=10, pady=(5, 0))
        self.p_bar = ctk.CTkProgressBar(self, height=8, progress_color="#2ecc71")
        self.p_bar.set(0)
        self.p_bar.pack(fill="x", padx=10, pady=5)
        self.stats = ctk.CTkLabel(self, text="Initializing...", font=("Arial", 10), text_color="#bdc3c7")
        self.stats.pack(fill="x", padx=10, pady=(0, 2))

        self.btn_row = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_row.pack(fill="x", padx=10, pady=5)
        self.pause_btn = ctk.CTkButton(self.btn_row, text="Pause", width=60, height=22, fg_color="#f39c12", command=lambda: pause_callback(self))
        self.pause_btn.pack(side="left", padx=2)
        self.cancel_btn = ctk.CTkButton(self.btn_row, text="Cancel", width=60, height=22, fg_color="#e74c3c", command=lambda: cancel_callback(self))
        self.cancel_btn.pack(side="left", padx=2)

    def update_stats(self, percent, speed, eta):
        try:
            p_val = float(percent.replace('%','').strip()) / 100
            self.p_bar.set(p_val)
            self.stats.configure(text=f"PAUSED | {percent}" if self.is_paused else f"{percent} | {speed} | ETA: {eta}")
        except: pass

class ProDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Pro Media Center - Ultimate Bypass Edition")
        self.geometry("1300x950")
        ctk.set_appearance_mode("Dark")
        self.vlc_instance = vlc.Instance("--no-xlib --quiet")
        self.player = self.vlc_instance.media_player_new()
        self._build_ui()
        self.update_loop()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3); self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self.left_panel = ctk.CTkFrame(self, fg_color="#1a1a1a"); self.left_panel.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.video_frame = ctk.CTkFrame(self.left_panel, fg_color="black"); self.video_frame.pack(fill="both", expand=True, padx=15, pady=15)
        self.player_overlay = ctk.CTkFrame(self.left_panel, fg_color="#252525", height=100); self.player_overlay.pack(fill="x", padx=15, pady=(0, 15))
        self.seek_slider = ctk.CTkSlider(self.player_overlay, from_=0, to=100, command=self.set_position); self.seek_slider.set(0); self.seek_slider.pack(fill="x", padx=20, pady=10)
        self.control_row = ctk.CTkFrame(self.player_overlay, fg_color="transparent"); self.control_row.pack(fill="x", pady=5)
        self.time_label = ctk.CTkLabel(self.control_row, text="00:00 / 00:00"); self.time_label.pack(side="left", padx=20)
        ctk.CTkButton(self.control_row, text="▶", width=40, command=self.player.play).pack(side="left", padx=5)
        ctk.CTkButton(self.control_row, text="⏸", width=40, command=self.player.pause).pack(side="left", padx=5)

        self.right_panel = ctk.CTkFrame(self, fg_color="#2c3e50"); self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        self.thumb_box = ctk.CTkLabel(self.right_panel, text="PREVIEW", width=280, height=150, fg_color="#1a1a1a", corner_radius=10); self.thumb_box.pack(pady=10, padx=20)
        self.url_entry = ctk.CTkEntry(self.right_panel, placeholder_text="Paste URL...", width=280); self.url_entry.pack(pady=5)
        self.analyze_btn = ctk.CTkButton(self.right_panel, text="ANALYZE", command=self.start_analysis); self.analyze_btn.pack(pady=5, padx=20, fill="x")
        self.format_combo = ctk.CTkComboBox(self.right_panel, values=["Quality (Size)"], width=280); self.format_combo.pack(pady=5)
        self.name_entry = ctk.CTkEntry(self.right_panel, placeholder_text="Filename", width=280); self.name_entry.pack(pady=5)
        self.download_btn = ctk.CTkButton(self.right_panel, text="ADD TO DOWNLOADS", state="disabled", fg_color="#27ae60", command=self.start_download); self.download_btn.pack(pady=10, padx=20, fill="x")
        self.queue_container = ctk.CTkScrollableFrame(self.right_panel, height=400, fg_color="#1e272e"); self.queue_container.pack(fill="both", expand=True, padx=10, pady=10)

    def _safe_vlc_refresh(self, media_url):
        try:
            self.player.stop(); time.sleep(0.2)
            win_id = self.video_frame.winfo_id()
            if platform.system() == "Windows": self.player.set_hwnd(win_id)
            else: self.player.set_xwindow(win_id)
            self.player.set_media(self.vlc_instance.media_new(media_url))
            self.player.play()
        except: pass

    def set_position(self, value):
        if self.player.get_length() > 0: self.player.set_position(float(value) / 100.0)

    def update_loop(self):
        if self.player.is_playing():
            curr, total = self.player.get_time() // 1000, self.player.get_length() // 1000
            if total > 0:
                self.seek_slider.set((curr / total) * 100)
                self.time_label.configure(text=f"{time.strftime('%M:%S', time.gmtime(curr))} / {time.strftime('%M:%S', time.gmtime(total))}")
        self.after(1000, self.update_loop)

    def start_analysis(self):
        url = self.url_entry.get()
        if not url: return
        self.analyze_btn.configure(state="disabled", text="ANALYZING...")
        threading.Thread(target=self.fetch_info, args=(url,), daemon=True).start()

    def fetch_info(self, url):
        # BYPASS OPTIONS
        opts = {
            'quiet': True, 
            'noplaylist': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': url,
            'no_check_certificate': True
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info.get('thumbnail'):
                    # Load thumbnail with headers to avoid 403
                    req = urllib.request.Request(info['thumbnail'], headers={'User-Agent': opts['user_agent']})
                    with urllib.request.urlopen(req) as u:
                        img = Image.open(BytesIO(u.read()))
                    self.after(0, lambda: self.thumb_box.configure(image=ctk.CTkImage(img, size=(280, 150)), text=""))

                self.after(0, lambda: self._safe_vlc_refresh(info.get('url', '')))
                
                title = info.get('title', 'video')[:30]
                formats = [f"{f.get('resolution', 'N/A')} ID:{f.get('format_id')}" for f in info.get('formats', []) if f.get('vcodec') != 'none']
                self.after(0, lambda: self.update_ui_post_analysis(title, formats))
        except Exception as e:
            print(f"Error: {e}")
            self.after(0, lambda: self.analyze_btn.configure(state="normal", text="ANALYZE"))

    def update_ui_post_analysis(self, title, formats):
        self.name_entry.delete(0, 'end'); self.name_entry.insert(0, title)
        self.format_combo.configure(values=formats)
        if formats: self.format_combo.set(formats[-1])
        self.download_btn.configure(state="normal"); self.analyze_btn.configure(state="normal", text="ANALYZE")

    def handle_pause(self, task):
        task.is_paused = not task.is_paused
        task.pause_btn.configure(text="Resume" if task.is_paused else "Pause")

    def handle_cancel(self, task):
        if messagebox.askyesno("Cancel", "Stop download?"): task.is_cancelled = True

    def start_download(self):
        path = filedialog.askdirectory()
        if not path: return
        url, name, fid = self.url_entry.get(), self.name_entry.get(), self.format_combo.get().split("ID:")[-1]
        task_ui = DownloadTask(self.queue_container, name, self.handle_pause, self.handle_cancel)
        threading.Thread(target=self.execute_download, args=(url, fid, path, name, task_ui), daemon=True).start()

    def execute_download(self, url, fid, path, name, task_ui):
        def progress_hook(d):
            if task_ui.is_cancelled: raise Exception("STOP")
            while task_ui.is_paused:
                if task_ui.is_cancelled: raise Exception("STOP")
                time.sleep(0.5)
            if d['status'] == 'downloading':
                self.after(0, lambda: task_ui.update_stats(d.get('_percent_str', '0%'), d.get('_speed_str', 'N/A'), d.get('_eta_str', 'N/A')))
            elif d['status'] == 'finished':
                self.after(0, lambda: task_ui.stats.configure(text="COMPLETE", text_color="#2ecc71"))

        opts = {
    'format': f'{fid}+bestaudio/best',
    'outtmpl': os.path.join(path, f"{name}.%(ext)s"),
    'progress_hooks': [progress_hook],
    'concurrent_fragment_downloads': 15, # Increased
    'buffersize': 1024*1024, # 1MB buffer
    'retries': 10,
    'fragment_retries': 10,
    'continuedl': True, # Important for resuming
    'quiet': True,
    'noprogress': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...', # As shown above
}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
        except Exception as e:
            if "STOP" in str(e): self.after(0, task_ui.destroy)
            else: self.after(0, lambda: task_ui.stats.configure(text="ERROR", text_color="#e74c3c"))

if __name__ == "__main__":
    app = ProDownloader(); app.mainloop()