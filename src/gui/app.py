import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading
import os
import sys

class AQCLauncher:
    def __init__(self, root):
        self.root = rootimport tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading
import os
import sys
import webbrowser
from pathlib import Path

class AQCLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("AQC System - Boss Edition")
        self.root.geometry("600x500")
        
        # Styles
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Helvetica', 10))
        style.configure("TLabel", font=('Helvetica', 10))

        # --- HEADER ---
        lbl_title = tk.Label(root, text="Automated Quality Control System", font=('Helvetica', 16, 'bold'))
        lbl_title.pack(pady=20)

        # --- INPUT FOLDER ---
        frame_in = ttk.LabelFrame(root, text="1. Select Video Source Folder", padding=10)
        frame_in.pack(fill="x", padx=20, pady=5)
        
        self.input_dir = tk.StringVar()
        entry_in = ttk.Entry(frame_in, textvariable=self.input_dir, width=50)
        entry_in.pack(side="left", padx=5)
        btn_in = ttk.Button(frame_in, text="Browse...", command=self.browse_input)
        btn_in.pack(side="left")

        # --- OUTPUT FOLDER ---
        frame_out = ttk.LabelFrame(root, text="2. Select Report Destination", padding=10)
        frame_out.pack(fill="x", padx=20, pady=5)
        
        self.output_dir = tk.StringVar()
        entry_out = ttk.Entry(frame_out, textvariable=self.output_dir, width=50)
        entry_out.pack(side="left", padx=5)
        btn_out = ttk.Button(frame_out, text="Browse...", command=self.browse_output)
        btn_out.pack(side="left")

        # --- PROFILE SELECTION ---
        frame_prof = ttk.LabelFrame(root, text="3. Select QC Profile", padding=10)
        frame_prof.pack(fill="x", padx=20, pady=5)
        
        self.profile = tk.StringVar(value="strict")
        profiles = [("Strict (Broadcast)", "strict"), ("YouTube (Web)", "youtube"), ("Netflix (HD Spec)", "netflix_hd")]
        
        for text, mode in profiles:
            rb = ttk.Radiobutton(frame_prof, text=text, variable=self.profile, value=mode)
            rb.pack(anchor="w")

        # --- RUN BUTTON ---
        self.btn_run = ttk.Button(root, text="START QC BATCH", command=self.start_thread)
        self.btn_run.pack(pady=20, ipadx=20, ipady=10)

        # --- STATUS ---
        self.status_var = tk.StringVar(value="Ready")
        lbl_status = tk.Label(root, textvariable=self.status_var, fg="blue")
        lbl_status.pack(pady=5)

    def browse_input(self):
        path = filedialog.askdirectory()
        if path: self.input_dir.set(path)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path: self.output_dir.set(path)

    def start_thread(self):
        if not self.input_dir.get() or not self.output_dir.get():
            messagebox.showwarning("Missing Info", "Please select both Input and Output folders.")
            return
        
        self.btn_run.config(state="disabled")
        self.status_var.set("Running... (Check Console for Progress)")
        
        # Run in separate thread to keep GUI responsive
        t = threading.Thread(target=self.run_docker)
        t.start()

    def run_docker(self):
        in_path = os.path.abspath(self.input_dir.get())
        out_path = os.path.abspath(self.output_dir.get())
        mode = self.profile.get()

        # Construct Docker Command
        # Note: We mount the host paths to /data/input and /data/output inside the container
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{in_path}:/data/input",
            "-v", f"{out_path}:/data/output",
            "aqc_system",
            "python", "batch_runner.py",
            "--input_dir", "/data/input",
            "--output_dir", "/data/output",
            "--mode", mode,
            "--workers", "4"
        ]

        try:
            # Run the Batch Process
            # On Windows, shell=True helps find the docker path, but usually not needed if PATH is set.
            # Using text=True to capture output if needed.
            process = subprocess.run(cmd, check=True, text=True)
            
            self.root.after(0, lambda: messagebox.showinfo("Success", "QC Batch Completed!"))
            
            # --- SMART RESULT OPENING ---
            
            # 1. Open the Output Folder Window (Always)
            if os.name == 'nt': # Windows
                os.startfile(out_path)
            elif sys.platform == 'darwin': # Mac
                subprocess.Popen(['open', out_path])
            else: # Linux
                subprocess.Popen(['xdg-open', out_path])

            # 2. Smart Browser Launch (Only if < 10 files)
            # Scan the output directory for "qc_report" folders
            report_dirs = [d for d in Path(out_path).iterdir() if d.is_dir() and d.name.endswith('_qc_report')]
            
            if len(report_dirs) > 0 and len(report_dirs) < 10:
                self.root.after(0, lambda: self.status_var.set(f"Opening {len(report_dirs)} reports in browser..."))
                for report_folder in report_dirs:
                    dashboard_path = report_folder / "dashboard.html"
                    if dashboard_path.exists():
                        webbrowser.open(dashboard_path.as_uri())
            
            # -----------------------------

            self.root.after(0, lambda: self.status_var.set("Done."))
            
        except subprocess.CalledProcessError as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Docker process failed.\nEnsure Docker Desktop is running.\n\nExit Code: {e.returncode}"))
            self.root.after(0, lambda: self.status_var.set("Failed."))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}"))
        finally:
            self.root.after(0, lambda: self.btn_run.config(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = AQCLauncher(root)
    root.mainloop()
        self.root.title("AQC System - Boss Edition")
        self.root.geometry("600x450")
        
        # Styles
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Helvetica', 10))
        style.configure("TLabel", font=('Helvetica', 10))

        # --- HEADER ---
        lbl_title = tk.Label(root, text="Automated Quality Control System", font=('Helvetica', 16, 'bold'))
        lbl_title.pack(pady=20)

        # --- INPUT FOLDER ---
        frame_in = ttk.LabelFrame(root, text="1. Select Video Source Folder", padding=10)
        frame_in.pack(fill="x", padx=20, pady=5)
        
        self.input_dir = tk.StringVar()
        entry_in = ttk.Entry(frame_in, textvariable=self.input_dir, width=50)
        entry_in.pack(side="left", padx=5)
        btn_in = ttk.Button(frame_in, text="Browse...", command=self.browse_input)
        btn_in.pack(side="left")

        # --- OUTPUT FOLDER ---
        frame_out = ttk.LabelFrame(root, text="2. Select Report Destination", padding=10)
        frame_out.pack(fill="x", padx=20, pady=5)
        
        self.output_dir = tk.StringVar()
        entry_out = ttk.Entry(frame_out, textvariable=self.output_dir, width=50)
        entry_out.pack(side="left", padx=5)
        btn_out = ttk.Button(frame_out, text="Browse...", command=self.browse_output)
        btn_out.pack(side="left")

        # --- PROFILE SELECTION ---
        frame_prof = ttk.LabelFrame(root, text="3. Select QC Profile", padding=10)
        frame_prof.pack(fill="x", padx=20, pady=5)
        
        self.profile = tk.StringVar(value="strict")
        profiles = [("Strict (Broadcast)", "strict"), ("YouTube (Web)", "youtube"), ("Netflix (HD Spec)", "netflix_hd")]
        
        for text, mode in profiles:
            rb = ttk.Radiobutton(frame_prof, text=text, variable=self.profile, value=mode)
            rb.pack(anchor="w")

        # --- RUN BUTTON ---
        self.btn_run = ttk.Button(root, text="START QC BATCH", command=self.start_thread)
        self.btn_run.pack(pady=20, ipadx=20, ipady=10)

        # --- STATUS ---
        self.status_var = tk.StringVar(value="Ready")
        lbl_status = tk.Label(root, textvariable=self.status_var, fg="blue")
        lbl_status.pack(pady=5)

    def browse_input(self):
        path = filedialog.askdirectory()
        if path: self.input_dir.set(path)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path: self.output_dir.set(path)

    def start_thread(self):
        if not self.input_dir.get() or not self.output_dir.get():
            messagebox.showwarning("Missing Info", "Please select both Input and Output folders.")
            return
        
        self.btn_run.config(state="disabled")
        self.status_var.set("Running... (Check Console for Progress)")
        
        # Run in separate thread to keep GUI responsive
        t = threading.Thread(target=self.run_docker)
        t.start()

    def run_docker(self):
        in_path = os.path.abspath(self.input_dir.get())
        out_path = os.path.abspath(self.output_dir.get())
        mode = self.profile.get()

        # Construct Docker Command
        # Note: We mount the host paths to /data/input and /data/output inside the container
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{in_path}:/data/input",
            "-v", f"{out_path}:/data/output",
            "aqc_system",
            "python", "batch_runner.py",
            "--input_dir", "/data/input",
            "--output_dir", "/data/output",
            "--mode", mode,
            "--workers", "4"
        ]

        try:
            # On Windows, we need shell=True to find the docker command easily in some envs
            # We capture output to print to the console window launching this app
            process = subprocess.run(cmd, check=True, text=True)
            
            self.root.after(0, lambda: messagebox.showinfo("Success", "QC Batch Completed!\nCheck the output folder."))
            self.root.after(0, lambda: self.status_var.set("Done."))
        except subprocess.CalledProcessError as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Docker process failed.\nEnsure Docker Desktop is running.\n\nError code: {e.returncode}"))
            self.root.after(0, lambda: self.status_var.set("Failed."))
        finally:
            self.root.after(0, lambda: self.btn_run.config(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = AQCLauncher(root)
    root.mainloop()