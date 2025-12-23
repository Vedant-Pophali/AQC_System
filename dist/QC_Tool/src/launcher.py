import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import threading
import sys
import os
from pathlib import Path

VERSION = "1.2 (Browser-Fixed)"

class QCLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Media QC Tool - v{VERSION}")
        self.root.geometry("600x450")
        self.root.resizable(False, False)

        # Header
        header = tk.Frame(root, pady=10)
        header.pack()
        tk.Label(header, text="Automated Media Quality Control",
                 font=("Segoe UI", 16, "bold")).pack()
        tk.Label(header, text="Visual • Audio • Vernacular OCR",
                 font=("Segoe UI", 10)).pack()

        # File Picker
        input_frame = tk.Frame(root, pady=10)
        input_frame.pack()

        tk.Label(input_frame, text="Select Video File:").pack(anchor="w", padx=20)

        self.file_entry = tk.Entry(input_frame, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=(20, 5))

        tk.Button(input_frame, text="Browse...",
                  command=self.browse_file).pack(side=tk.LEFT)

        # Run Button
        self.btn_run = tk.Button(
            root,
            text="START QC ANALYSIS",
            font=("Segoe UI", 11, "bold"),
            bg="#0078D7",
            fg="white",
            height=2,
            width=22,
            command=self.start_thread
        )
        self.btn_run.pack(pady=15)

        # Log Area
        tk.Label(root, text="Process Log:").pack(anchor="w", padx=20)
        self.log_area = scrolledtext.ScrolledText(
            root, width=70, height=12,
            state='disabled', font=("Consolas", 9)
        )
        self.log_area.pack(padx=20, pady=5)

        self.lbl_status = tk.Label(root, text="Ready", fg="gray")
        self.lbl_status.pack(side=tk.BOTTOM, pady=5)

    # ---------------- UI HELPERS ----------------

    def browse_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi")]
        )
        if path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, path)

    def log(self, msg):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    # ---------------- THREAD CONTROL ----------------

    def start_thread(self):
        video_path = self.file_entry.get()

        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Error", "Select a valid video file.")
            return

        self.btn_run.config(state='disabled', text="Processing...")
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')

        threading.Thread(
            target=self.run_pipeline,
            args=(video_path,),
            daemon=True
        ).start()

    # ---------------- CORE LOGIC ----------------

    def run_pipeline(self, video_path):
        try:
            self.log("--- STARTING PIPELINE ---")
            self.log(f"Target: {os.path.basename(video_path)}")

            base_dir = os.path.dirname(__file__)
            main_script = os.path.join(base_dir, "main.py")

            process = subprocess.Popen(
                [sys.executable, main_script, "--input", video_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            for line in process.stdout:
                self.log(line.rstrip())

            process.wait()

            if process.returncode != 0:
                raise RuntimeError("Pipeline failed")

            self.lbl_status.config(text="Job Complete", fg="green")

            # Resolve dashboard path
            reports_dir = os.path.join(
                os.path.dirname(base_dir), "reports"
            )
            dashboard = os.path.join(reports_dir, "dashboard.html")

            if os.path.exists(dashboard):
                self.log("Opening dashboard in browser...")
                self.root.after(0, self.open_dashboard, dashboard)
            else:
                self.log("[WARN] Dashboard not found")

            messagebox.showinfo("Success", "QC Analysis Completed!")

        except Exception as e:
            self.lbl_status.config(text="Failed", fg="red")
            self.log(f"[CRITICAL] {e}")
            messagebox.showerror("Error", str(e))

        finally:
            self.btn_run.config(state='normal', text="START QC ANALYSIS")

    # ---------------- BROWSER FIX ----------------

    def open_dashboard(self, path):
        """Guaranteed browser open (Windows-safe, thread-safe)"""
        try:
            uri = Path(path).resolve().as_uri()

            if sys.platform.startswith("win"):
                subprocess.Popen(
                    ["cmd", "/c", "start", "", uri],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                subprocess.Popen(["xdg-open", uri])

        except Exception as e:
            self.log(f"[BROWSER ERROR] {e}")

# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":
    root = tk.Tk()
    app = QCLauncher(root)
    root.mainloop()
