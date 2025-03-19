#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
import json
import os
import subprocess

# Default file where the configuration will be saved
CONFIG_FILE = "server_config.json"

# Path to your main fuzzing script (the one with parse_arguments())
SCRIPT_PATH = "./fuzzer_with_ui.py"

def save_config():
    """
    Save the configuration to server_config.json inside the output directory.
    This does not affect the main script unless you modify the script to read from JSON.
    """
    if not output_dir_var.get() or not os.path.isdir(output_dir_var.get()):
        messagebox.showerror("Error", "Please select a valid output directory.")
        return

    config = {
        "OUTPUT_DIR": output_dir_var.get(),
        "RTSP_SERVER_IP": rtsp_ip_var.get(),
        "RTSP_SERVER_PORT": rtsp_port_var.get(),
        "SERVER_EXECUTABLE": server_exec_var.get(),
        "COVERAGE_DIR": coverage_dir_var.get(),
        "stop_mode": stop_mode_var.get(),
        "time_duration": time_duration_var.get() if stop_mode_var.get() == "time" else None,
        "mutation_count": mutation_count_var.get() if stop_mode_var.get() == "mutation" else None,
        "json_file": json_file_var.get()
    }

    # Save server_config.json in the output directory
    config_path = os.path.join(output_dir_var.get(), CONFIG_FILE)
    try:
        with open(config_path, 'w') as config_file:
            json.dump(config, config_file, indent=4)
        messagebox.showinfo("Configuration Saved",
                            f"Configuration saved successfully in {config_path}.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save configuration: {e}")

def browse_directory(var):
    directory = filedialog.askdirectory()
    if directory:
        var.set(directory)

def browse_file(var):
    file_path = filedialog.askopenfilename()
    if file_path:
        var.set(file_path)

def toggle_stop_mode_fields(*args):
    """
    Enable/disable fields based on whether user chooses 'time' or 'mutation'.
    """
    if stop_mode_var.get() == "time":
        time_duration_entry.config(state="normal")
        mutation_count_entry.config(state="disabled")
    else:
        time_duration_entry.config(state="disabled")
        mutation_count_entry.config(state="normal")

def start_server():
    """
    Save config and start the main fuzzing script with the correct arguments.
    """
    save_config()
    if not validate_fields():
        return

    # Build the command line to run the main script
    try:
        command = [
            "python3", SCRIPT_PATH,
            "--stop_mode", stop_mode_var.get()
        ]

        # If user picked time-based stop mode, pass --time_duration
        if stop_mode_var.get() == "time":
            command += ["--time_duration", time_duration_var.get()]

        # If user picked mutation-based stop mode, pass --mutation_count
        if stop_mode_var.get() == "mutation":
            command += ["--mutation_count", mutation_count_var.get()]

        # Always pass the JSON file (your main script uses default if not specified,
        # but let's pass the user-chosen file)
        if json_file_var.get():
            command += ["--json_file", json_file_var.get()]

        # If you want to pass IP/port/etc., you must also add those arguments to the
        # parse_arguments() in the main script. Example:
        # command += ["--rtsp_server_ip", rtsp_ip_var.get()]
        # command += ["--rtsp_server_port", rtsp_port_var.get()]

        subprocess.Popen(command)
        messagebox.showinfo("Server Started", "Server started successfully using sample_12.py.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start the server: {e}")

def validate_fields():
    """
    Make sure the user provided valid values for directories, files, etc.
    """
    if not output_dir_var.get() or not os.path.isdir(output_dir_var.get()):
        messagebox.showerror("Error", "Please select a valid output directory.")
        return False
    if not server_exec_var.get() or not os.path.isfile(server_exec_var.get()):
        messagebox.showerror("Error", "Please select a valid server executable.")
        return False

    # If the user picked time-based mode, time_duration must be an integer
    if stop_mode_var.get() == "time":
        if not time_duration_var.get().isdigit():
            messagebox.showerror("Error", "Please enter a valid time duration (integer).")
            return False

    # If the user picked mutation-based mode, mutation_count must be an integer
    if stop_mode_var.get() == "mutation":
        if not mutation_count_var.get().isdigit():
            messagebox.showerror("Error", "Please enter a valid mutation count (integer).")
            return False

    return True

def exit_app():
    root.quit()

# Main UI window
root = tk.Tk()
root.title("RTSP Server Configuration")
root.geometry("750x450")
root.configure(bg="#f0f2f5")
root.resizable(False, False)

# Set a theme
style = ttk.Style(root)
style.theme_use("clam")  # or "vista", "default", etc.
style.configure("TLabel", background="#f0f2f5", font=("Helvetica", 12))
style.configure("TButton", font=("Helvetica", 12))
style.configure("TEntry", font=("Helvetica", 12))
style.configure("TCheckbutton", background="#f0f2f5", font=("Helvetica", 12))

# Variables
output_dir_var = tk.StringVar()
rtsp_ip_var = tk.StringVar(value="131.188.37.115")
rtsp_port_var = tk.StringVar(value="8554")
server_exec_var = tk.StringVar()
coverage_dir_var = tk.StringVar()

# This is the important one: matches --stop_mode in main script
stop_mode_var = tk.StringVar(value="time")

# Matches --time_duration in main script
time_duration_var = tk.StringVar(value="60")

# Matches --mutation_count in main script
mutation_count_var = tk.StringVar(value="500")

# If you want to let user pick a JSON file for --json_file
json_file_var = tk.StringVar(value="oracle_map_client_9.json")

# Main Frame
frame = ttk.Frame(root, padding="20")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

# Title Label
title_label = ttk.Label(frame, text="RTSP Server Configuration", font=("Helvetica", 18, "bold"))
title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

# Layout for configuration fields
ttk.Label(frame, text="Output Directory:").grid(row=1, column=0, sticky="e", pady=5)
output_dir_entry = ttk.Entry(frame, textvariable=output_dir_var, width=50)
output_dir_entry.grid(row=1, column=1, padx=5)
ttk.Button(frame, text="Browse...", command=lambda: browse_directory(output_dir_var)).grid(row=1, column=2, padx=5)

ttk.Label(frame, text="RTSP Server IP:").grid(row=2, column=0, sticky="e", pady=5)
rtsp_ip_entry = ttk.Entry(frame, textvariable=rtsp_ip_var, width=50)
rtsp_ip_entry.grid(row=2, column=1, padx=5)

ttk.Label(frame, text="RTSP Server Port:").grid(row=3, column=0, sticky="e", pady=5)
rtsp_port_entry = ttk.Entry(frame, textvariable=rtsp_port_var, width=50)
rtsp_port_entry.grid(row=3, column=1, padx=5)

ttk.Label(frame, text="Server Executable:").grid(row=4, column=0, sticky="e", pady=5)
server_exec_entry = ttk.Entry(frame, textvariable=server_exec_var, width=50)
server_exec_entry.grid(row=4, column=1, padx=5)
ttk.Button(frame, text="Browse...", command=lambda: browse_file(server_exec_var)).grid(row=4, column=2, padx=5)

ttk.Label(frame, text="Coverage Directory:").grid(row=5, column=0, sticky="e", pady=5)
coverage_dir_entry = ttk.Entry(frame, textvariable=coverage_dir_var, width=50)
coverage_dir_entry.grid(row=5, column=1, padx=5)
ttk.Button(frame, text="Browse...", command=lambda: browse_directory(coverage_dir_var)).grid(row=5, column=2, padx=5)

ttk.Label(frame, text="Stop Mode:").grid(row=6, column=0, sticky="e", pady=5)
stop_mode_menu = ttk.OptionMenu(frame, stop_mode_var, "time", "time", "mutation")
stop_mode_menu.grid(row=6, column=1, sticky="w")

ttk.Label(frame, text="Time Duration (s):").grid(row=7, column=0, sticky="e", pady=5)
time_duration_entry = ttk.Entry(frame, textvariable=time_duration_var, width=50)
time_duration_entry.grid(row=7, column=1, padx=5)

ttk.Label(frame, text="Mutation Count:").grid(row=8, column=0, sticky="e", pady=5)
mutation_count_entry = ttk.Entry(frame, textvariable=mutation_count_var, width=50)
mutation_count_entry.grid(row=8, column=1, padx=5)

ttk.Label(frame, text="JSON File:").grid(row=9, column=0, sticky="e", pady=5)
json_file_entry = ttk.Entry(frame, textvariable=json_file_var, width=50)
json_file_entry.grid(row=9, column=1, padx=5)
ttk.Button(frame, text="Browse...", command=lambda: browse_file(json_file_var)).grid(row=9, column=2, padx=5)

# Button Frame
button_frame = ttk.Frame(frame)
button_frame.grid(row=10, column=0, columnspan=3, pady=(20, 0))

ttk.Button(button_frame, text="Save Configuration", command=save_config).grid(row=0, column=0, padx=10)
ttk.Button(button_frame, text="Start Server", command=start_server).grid(row=0, column=1, padx=10)
ttk.Button(button_frame, text="Exit", command=exit_app).grid(row=0, column=2, padx=10)

# Automatically enable/disable time/mutation fields
stop_mode_var.trace("w", toggle_stop_mode_fields)
toggle_stop_mode_fields()

root.mainloop()

