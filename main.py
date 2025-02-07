# Below is the entire code with persistence for Tesseract path, base_speed, text_speed, and region_box.
# Changes:
# 1. Added imports for json and os.
# 2. Added load_config() and save_config() functions.
# 3. Replaced hardcoded Tesseract path, base_speed, text_speed, and region_box with config-based values.
# 4. Updated update_settings() and select_region() to save new values to config.json.

import json
import os
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import time

import pyautogui
from PIL import ImageGrab
import pytesseract
from pynput import mouse, keyboard

# ================= Configuration & Persistence =================

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # Default values if config.json doesn't exist or is invalid.
    return {
        "tesseract_path": "",
        "base_speed": 110,
        "text_speed": 60,
        "region_box": None
    }


def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except IOError:
        pass

# Load config at startup
config = load_config()

# Apply config values
pytesseract.pytesseract.tesseract_cmd = config.get("tesseract_path", "")
base_speed = config.get("base_speed", 110)
text_speed = config.get("text_speed", 60)
region_box = config.get("region_box", None)

# Flag to indicate whether auto-scroll is active.
auto_scrolling = False

# Fixed timing constants (in seconds)
initial_delay = 0.07    # Delay after activation before starting OCR/scrolling
scroll_interval = 0.05  # Interval between OCR checks

# ================= Debug Logging Setup =================

# Global reference to the debug text widget
debug_text_widget = None

def safe_debug_log(msg):
    """Safely log a message both to the console and to the debug window (if open)."""
    print(msg)
    if debug_text_widget is not None:
        # Use after() to safely update the Text widget from any thread.
        debug_text_widget.after(0, lambda: (debug_text_widget.insert(tk.END, msg + "\n"),
                                            debug_text_widget.see(tk.END)))

# ================= UI Widget Variables (set later) =================

root = None
region_label = None
tesseract_entry = None
base_speed_entry = None
text_speed_entry = None

# ================= Function: Update Settings =================

def update_settings():
    """Update global settings from the UI entry fields and config, then save them."""
    global base_speed, text_speed
    new_tesseract_path = tesseract_entry.get()
    config["tesseract_path"] = new_tesseract_path
    pytesseract.pytesseract.tesseract_cmd = new_tesseract_path

    try:
        base_speed = int(base_speed_entry.get())
    except ValueError:
        base_speed = 70
    try:
        text_speed = int(text_speed_entry.get())
    except ValueError:
        text_speed = 30

    config["base_speed"] = base_speed
    config["text_speed"] = text_speed
    save_config(config)

    safe_debug_log("Settings updated:")
    safe_debug_log("  Tesseract: " + pytesseract.pytesseract.tesseract_cmd)
    safe_debug_log("  Base Movement (px): " + str(base_speed))
    safe_debug_log("  Text-Detected Movement (px): " + str(text_speed))

# ================= Function: Region Selection =================

def select_region():
    """
    Launch a full-screen transparent overlay so you can click and drag to select an OCR region.
    The selected region is stored in the global variable `region_box`.
    """
    global region_box, region_label, root

    overlay = tk.Toplevel(root)
    overlay.attributes("-fullscreen", True)
    overlay.attributes("-alpha", 0.3)  # Semi-transparent overlay
    overlay.overrideredirect(True)     # Remove window borders

    canvas = tk.Canvas(overlay, cursor="cross", bg="grey")
    canvas.pack(fill="both", expand=True)

    start_x = start_y = 0
    rect = None

    def on_button_press(event):
        nonlocal start_x, start_y, rect
        start_x = event.x
        start_y = event.y
        rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

    def on_move(event):
        nonlocal rect
        canvas.coords(rect, start_x, start_y, event.x, event.y)

    def on_button_release(event):
        nonlocal start_x, start_y, rect
        global region_box
        end_x, end_y = event.x, event.y
        x1, y1 = min(start_x, end_x), min(start_y, end_y)
        x2, y2 = max(start_x, end_x), max(start_y, end_y)
        region_box = (x1, y1, x2, y2)
        region_label.config(text=f"Region: {region_box}")
        config["region_box"] = region_box
        save_config(config)
        overlay.destroy()
        safe_debug_log("Region selected: " + str(region_box))

    canvas.bind("<ButtonPress-1>", on_button_press)
    canvas.bind("<B1-Motion>", on_move)
    canvas.bind("<ButtonRelease-1>", on_button_release)

# ================= Function: Auto-Scroll with Parallel OCR =================

def auto_scroll_function():
    """
    After a short fixed delay, repeatedly check the OCR region by running two concurrent OCR workers.

    The function records the current mouse position as the origin.
    Two worker threads run concurrently, each capturing the OCR region and updating a shared dictionary.
    Every 0.05 seconds the main loop checks both workers’ latest OCR results:
      - If either worker detects text (non-empty), the mouse is set to (origin_x, origin_y + text_speed).
      - Otherwise, the mouse is set to (origin_x, origin_y + base_speed).

    The mouse is always positioned absolutely relative to the origin.
    """
    global auto_scrolling, region_box
    time.sleep(initial_delay)
    if not auto_scrolling:
        return

    origin_x, origin_y = pyautogui.position()
    safe_debug_log("Auto-scroll started with origin: " + str((origin_x, origin_y)))

    # Shared dictionary for OCR results and a lock for thread safety.
    ocr_results = {"worker1": "", "worker2": ""}
    ocr_lock = threading.Lock()

    def ocr_worker(worker_id):
        while auto_scrolling:
            if region_box is not None:
                try:
                    screenshot = ImageGrab.grab(bbox=region_box)
                    result = pytesseract.image_to_string(screenshot).strip()
                except Exception as e:
                    safe_debug_log("OCR error in " + worker_id + ": " + str(e))
                    result = ""
            else:
                result = ""
            with ocr_lock:
                ocr_results[worker_id] = result
            time.sleep(0.01)  # Small sleep to allow rapid polling

    # Start two OCR worker threads.
    threading.Thread(target=ocr_worker, args=("worker1",), daemon=True).start()
    threading.Thread(target=ocr_worker, args=("worker2",), daemon=True).start()

    while auto_scrolling:
        with ocr_lock:
            res1 = ocr_results.get("worker1", "")
            res2 = ocr_results.get("worker2", "")
        if res1 or res2:
            target_y = origin_y + text_speed
            safe_debug_log("Text detected; setting mouse to " + str((origin_x, target_y)))
        else:
            target_y = origin_y + base_speed
            safe_debug_log("No text detected; setting mouse to " + str((origin_x, target_y)))
        pyautogui.moveTo(origin_x, target_y, duration=0.05)
        time.sleep(scroll_interval)
    safe_debug_log("Auto-scroll stopped.")

# ================= Mouse & Keyboard Listener Callbacks =================

def on_mouse_click(x, y, button, pressed):
    """
    Mouse click handler:
      - On a middle-mouse press (if auto-scroll is not active), start auto-scroll.
      - On any other mouse button press, stop auto-scroll.
    """
    global auto_scrolling
    if pressed:
        if button == mouse.Button.middle:
            if not auto_scrolling:
                auto_scrolling = True
                threading.Thread(target=auto_scroll_function, daemon=True).start()
        else:
            if auto_scrolling:
                auto_scrolling = False


def on_key_press(key):
    """
    Keyboard press handler: stops auto-scroll if it is active.
    """
    global auto_scrolling
    if auto_scrolling:
        auto_scrolling = False

# ================= Debug Window =================

def open_debug_window():
    """Open a new window to display debug logs."""
    global debug_text_widget
    if debug_text_widget is None or not tk.Toplevel.winfo_exists(debug_text_widget.master):
        win = tk.Toplevel(root)
        win.title("Debug Log")
        debug_text_widget = tk.Text(win, wrap="word", width=80, height=20)
        debug_text_widget.pack(expand=True, fill="both")
    else:
        safe_debug_log("Debug window already open.")

# ================= Main UI Setup =================

def main():
    global root, region_label, tesseract_entry, base_speed_entry, text_speed_entry

    root = tk.Tk()
    root.title("Webtoon Reader Auto-Scroll")

    # --- Settings Frame ---
    settings_frame = ttk.LabelFrame(root, text="Settings", padding=10)
    settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

    ttk.Label(settings_frame, text="Tesseract Path:").grid(row=0, column=0, sticky="w")
    tesseract_entry = ttk.Entry(settings_frame, width=50)
    tesseract_entry.insert(0, pytesseract.pytesseract.tesseract_cmd)
    tesseract_entry.grid(row=0, column=1, padx=5, pady=2)

    # Button to browse for Tesseract.exe
    def browse_tesseract():
        path = filedialog.askopenfilename(filetypes=[("Executable Files", "*.exe")])
        if path:
            tesseract_entry.delete(0, tk.END)
            tesseract_entry.insert(0, path)

    browse_btn = ttk.Button(settings_frame, text="Browse...", command=browse_tesseract)
    browse_btn.grid(row=0, column=2, padx=5, pady=2)

    ttk.Label(settings_frame, text="Base Movement (px):").grid(row=1, column=0, sticky="w")
    base_speed_entry = ttk.Entry(settings_frame, width=10)
    base_speed_entry.insert(0, str(base_speed))
    base_speed_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")

    ttk.Label(settings_frame, text="Text-Detected Movement (px):").grid(row=2, column=0, sticky="w")
    text_speed_entry = ttk.Entry(settings_frame, width=10)
    text_speed_entry.insert(0, str(text_speed))
    text_speed_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

    update_btn = ttk.Button(settings_frame, text="Update Settings", command=update_settings)
    update_btn.grid(row=3, column=0, columnspan=3, pady=5)

    debug_btn = ttk.Button(settings_frame, text="Open Debug", command=open_debug_window)
    debug_btn.grid(row=4, column=0, columnspan=3, pady=5)

    # --- Region Selection Frame ---
    region_frame = ttk.LabelFrame(root, text="OCR Region Selection", padding=10)
    region_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

    select_region_btn = ttk.Button(region_frame, text="Select Screen Region", command=select_region)
    select_region_btn.grid(row=0, column=0, padx=5, pady=5)

    current_region = "Region: " + (str(region_box) if region_box else "Not set")
    region_label = ttk.Label(region_frame, text=current_region)
    region_label.grid(row=0, column=1, padx=5, pady=5)

    # --- Instructions ---
    instructions = (
        "Steps:\n"
        "1. Change settings as needed and click 'Update Settings'.\n"
        "2. Select the screen region for OCR (this is required).\n"
        "3. To start auto-scroll, press the middle mouse button.\n"
        "4. To stop auto-scroll, click any other mouse button or press any key."
    )
    instr_label = ttk.Label(root, text=instructions, justify="left")
    instr_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")

    # --- Global Mouse and Keyboard Listeners ---
    mouse_listener = mouse.Listener(on_click=on_mouse_click)
    mouse_listener.daemon = True
    mouse_listener.start()

    key_listener = keyboard.Listener(on_press=on_key_press)
    key_listener.daemon = True
    key_listener.start()

    root.mainloop()

if __name__ == "__main__":
    main()
