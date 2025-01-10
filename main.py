import sys
import time
import threading
import pyautogui
import keyboard
import pytesseract
from PIL import ImageGrab, ImageDraw
import tkinter as tk

# For mouse (pynput) to detect the middle mouse button
from pynput import mouse
from pynput.mouse import Button

# -----------------------------------------------------------------------------
# Set the path to your Tesseract executable
# -----------------------------------------------------------------------------
pytesseract.pytesseract.tesseract_cmd = r"E:\Tesseract-OCR\tesseract.exe"

# -----------------------------------------------------------------------------
# Configurable Variables (Top)
# -----------------------------------------------------------------------------

custom_config = r"--psm 11 --oem 3"
base_scroll_down = 70            # Starting scroll speed
scroll_up_on_text_detected = 30  # Slowdown when text is detected
scroll_max = 100                 # Cap scrolling speed
ocr_frequency = 0.2              # Interval between OCR checks
sleep_time = 0.3                # Delay before scrolling starts

# Internal real-time adjustments
SCROLL_UP_ADJUST = scroll_up_on_text_detected
BASE_SCROLL_DOWN = base_scroll_down
SCROLL_MAX = scroll_max
OCR_FREQUENCY = ocr_frequency

DEBUG_MODE = True

# -----------------------------------------------------------------------------
# Global State
# -----------------------------------------------------------------------------

stop_script = False
text_detected = False
scroll_active = False
origin_y = 0
current_scroll_speed = 0
ocr_region = None  # (left, top, width, height)
text_was_found = False
no_text_in_a_row = 0
immediate_jump = True    # If True, we teleport. If False, we move in steps.
scroll_step_size = 2      # Used only if immediate_jump is False.
incremental_jump = False  # If True, we move in steps. If False, we teleport.

# -----------------------------------------------------------------------------
# Tkinter-based OCR Region Selection
# -----------------------------------------------------------------------------

def select_area():
    """
    Let the user click-and-drag a red rectangle on a fullscreen translucent Tk window.
    Returns a dict {'top':..., 'left':..., 'width':..., 'height':...} or None if invalid.
    """
    selection_dict = None
    start_x, start_y = None, None

    def on_press(event):
        nonlocal start_x, start_y
        start_x, start_y = event.x, event.y
        canvas.delete("selection")
        if DEBUG_MODE:
            print(f"[Info] Selection started at: ({start_x}, {start_y})")

    def on_drag(event):
        if start_x is not None and start_y is not None:
            canvas.delete("selection")
            end_x, end_y = event.x, event.y
            canvas.create_rectangle(
                start_x, start_y, end_x, end_y,
                outline="red", fill="red", stipple="gray12", width=2, tags="selection"
            )

    def on_release(event):
        nonlocal selection_dict
        end_x, end_y = event.x, event.y
        left = min(start_x, end_x)
        top = min(start_y, end_y)
        width = abs(end_x - start_x)
        height = abs(end_y - start_y)
        if width > 0 and height > 0:
            selection_dict = {'top': top, 'left': left, 'width': width, 'height': height}
            if DEBUG_MODE:
                print(f"[Selection] Selected area: {selection_dict}")
        else:
            print("[Error] Invalid area selection. Please try again.")
            selection_dict = None
        root.destroy()

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.3)  # 30% opacity
    root.configure(bg='white')

    canvas = tk.Canvas(root, bg='white', highlightthickness=0)
    canvas.pack(fill='both', expand=True)

    canvas.bind('<Button-1>', on_press)
    canvas.bind('<B1-Motion>', on_drag)
    canvas.bind('<ButtonRelease-1>', on_release)

    canvas.create_text(
        root.winfo_screenwidth() // 2,
        50,
        text="Drag to select the area for text detection. Release to confirm.",
        fill="black",
        font=("Helvetica", 16)
    )

    root.mainloop()
    return selection_dict

def select_ocr_region():
    """
    Wrapper to convert the dict from select_area() into a (left, top, width, height) tuple.
    """
    area = select_area()
    if area is None:
        print("[Info] No valid selection made. Exiting.")
        sys.exit(1)
    return (area['left'], area['top'], area['width'], area['height'])

# -----------------------------------------------------------------------------
# OCR Loop
# -----------------------------------------------------------------------------

def ocr_loop():
    global stop_script, text_detected, ocr_region
    global no_text_in_a_row, origin_y, BASE_SCROLL_DOWN
    # We'll introduce a new global (or local) boolean:
    global text_was_found

    check_counter = 0
    try:
        while not stop_script:
            if DEBUG_MODE:
                dots = "." * (check_counter % 3 + 1)
                print(f"Checking{dots}")
                check_counter += 1

            if ocr_region:
                left, top, width, height = ocr_region
                bbox = (left, top, left + width, top + height)
                screenshot = ImageGrab.grab(bbox)

                if DEBUG_MODE:
                    draw = ImageDraw.Draw(screenshot)
                    draw.rectangle([0, 0, width, height], outline="red", width=3)

                text = pytesseract.image_to_string(screenshot)

                # ---------------------------------------------------------
                # 1) Check if we found any text
                # ---------------------------------------------------------
                if text.strip():
                    text_detected = True
                    text_was_found = True      # We did find text
                    no_text_in_a_row = 0      # Reset counter
                    if DEBUG_MODE:
                        print("Text Found!")
                else:
                    text_detected = False
                    
                    # -----------------------------------------------------
                    # 2) If text_was_found is True, increment no_text_in_a_row
                    # -----------------------------------------------------
                    if text_was_found:
                        no_text_in_a_row += 1
                        
                        if DEBUG_MODE:
                            print(f"No text found. Consecutive misses: {no_text_in_a_row}")
                        
                        # -------------------------------------------------
                        # 3) After 3 consecutive misses, reset to base
                        #    ONLY if we previously saw text (text_was_found=True)
                        # -------------------------------------------------
                        if no_text_in_a_row >= 3:
                            if DEBUG_MODE:
                                print("[OCR] 3 consecutive checks with NO text. Resetting scroll to base.")
                            
                            current_pos = pyautogui.position()
                            desired_y = origin_y + BASE_SCROLL_DOWN
                            
                            # Move pointer so distance = BASE_SCROLL_DOWN from origin
                            pyautogui.moveTo(current_pos.x, desired_y)
                            
                            # Optionally, reset text_was_found to False
                            # so we only do one reset per text-found session
                            text_was_found = False
                            
                            # Also reset the no_text_in_a_row counter
                            no_text_in_a_row = 0

                    else:
                        # If we haven't found text at all yet, do nothing special
                        # no_text_in_a_row remains 0, or we can track separately if needed
                        pass
            else:
                text_detected = False

            # Sleep for the normal OCR frequency
            time.sleep(OCR_FREQUENCY)

    except pytesseract.TesseractError:
        print("[Error] OCR Module Failure")
        stop_script = True
    except Exception as e:
        print("[Error] Unexpected Error in OCR:", e)
        stop_script = True

# -----------------------------------------------------------------------------
# Scrolling Logic
# -----------------------------------------------------------------------------

def handle_middle_click():
    global scroll_active, origin_y, current_scroll_speed
    scroll_active = not scroll_active
    if scroll_active:
        origin_y = pyautogui.position().y
        current_scroll_speed = 0
        
        time.sleep(sleep_time)
        # Possibly moves the mouse down right away by BASE_SCROLL_DOWN:
        current_pos = pyautogui.position()
        pyautogui.moveTo(current_pos.x, current_pos.y + BASE_SCROLL_DOWN)
        
        origin_y += BASE_SCROLL_DOWN  # updating origin if you do that

    else:
        # Stop scrolling
        current_scroll_speed = 0
        if DEBUG_MODE:
            print("[Scroll] Deactivated - Middle button pressed again")

def scroll_control_loop():
    """
    Monitors the mouse position during scrolling.
    If scrolling is active:
      - The distance from origin_y sets the 'target_speed'.
      - If text_detected and target_speed > 0, reduce it by SCROLL_UP_ADJUST.
      - Then either:
          A) If immediate_jump == True -> Teleport directly to origin_y + target_speed
          B) If immediate_jump == False -> Move up/down by 'scroll_step_size' increments
      - Clamp so we never go above origin_y.
    """
    global scroll_active, current_scroll_speed, stop_script

    while not stop_script:
        if scroll_active:
            current_pos = pyautogui.position()
            current_y = current_pos.y

            # How far below (or above) origin the mouse is
            distance = current_y - origin_y
            target_speed = distance

            # Cap speed
            if target_speed > SCROLL_MAX:
                target_speed = SCROLL_MAX
            elif target_speed < -SCROLL_MAX:
                target_speed = -SCROLL_MAX

            # If there's text, reduce downward speed
            if text_detected and target_speed > 0:
                target_speed -= SCROLL_UP_ADJUST
                if target_speed < 0:
                    target_speed = 0

            current_scroll_speed = target_speed

            # -----------------------------
            # Teleport vs. Incremental
            # -----------------------------
            if immediate_jump:
                # TELEPORT: Jump directly to origin_y + target_speed
                new_y = origin_y + current_scroll_speed
            else:
                # INCREMENTAL: Move by scroll_step_size up/down
                if current_scroll_speed > 0:
                    # Move down scroll_step_size
                    new_y = current_y + scroll_step_size
                elif current_scroll_speed < 0:
                    # Move up scroll_step_size
                    new_y = current_y - scroll_step_size
                else:
                    # No movement if speed == 0
                    new_y = current_y

            # Never go above origin_y
            if new_y < origin_y:
                new_y = origin_y

            # Perform the move
            pyautogui.moveTo(current_pos.x, new_y)

        time.sleep(0.01)

# -----------------------------------------------------------------------------
# Keybind Handlers (Keyboard)
# -----------------------------------------------------------------------------

def increase_base_down():
    global BASE_SCROLL_DOWN
    BASE_SCROLL_DOWN += 1
    print(f"Base scroll down increased: {BASE_SCROLL_DOWN}")

def increase_base_up():
    global SCROLL_UP_ADJUST
    SCROLL_UP_ADJUST += 1
    print(f"Base scroll up increased: {SCROLL_UP_ADJUST}")

def decrease_up_adjust():
    global SCROLL_UP_ADJUST
    SCROLL_UP_ADJUST -= 1
    if SCROLL_UP_ADJUST < 0:
        SCROLL_UP_ADJUST = 0
    print(f"Scroll up on text detected decreased: {SCROLL_UP_ADJUST}")

def increase_up_adjust():
    global SCROLL_UP_ADJUST
    SCROLL_UP_ADJUST += 1
    print(f"Scroll up on text detected increased: {SCROLL_UP_ADJUST}")

def increase_ocr_freq():
    global OCR_FREQUENCY
    OCR_FREQUENCY += 0.1
    print(f"OCR check interval increased: {OCR_FREQUENCY}")

def decrease_ocr_freq():
    global OCR_FREQUENCY
    if OCR_FREQUENCY > 0.1:
        OCR_FREQUENCY -= 0.1
    print(f"OCR check interval decreased: {OCR_FREQUENCY}")

def toggle_immediate_jump():
    global immediate_jump
    immediate_jump = not immediate_jump
    print(f"[ScrollMode] immediate_jump is now {immediate_jump}")

def increase_scroll_step():
    global scroll_step_size
    scroll_step_size += 1
    print(f"[ScrollMode] scroll_step_size = {scroll_step_size}")

def decrease_scroll_step():
    global scroll_step_size
    scroll_step_size -= 1
    if scroll_step_size < 1:
        scroll_step_size = 1
    print(f"[ScrollMode] scroll_step_size = {scroll_step_size}")

def init_keybinds():
    # We still use the keyboard library for these key triggers
    keyboard.add_hotkey(",", increase_base_down)
    keyboard.add_hotkey(".", increase_base_up)
    keyboard.add_hotkey(";", decrease_up_adjust)
    keyboard.add_hotkey("'", increase_up_adjust)
    keyboard.add_hotkey("[", increase_ocr_freq)
    keyboard.add_hotkey("]", decrease_ocr_freq)
    keyboard.add_hotkey("t", toggle_immediate_jump)
    keyboard.add_hotkey("=", increase_scroll_step)
    keyboard.add_hotkey("-", decrease_scroll_step)
    # Not adding "middle" here, because keyboard cannot detect mouse buttons

# -----------------------------------------------------------------------------
# Mouse Listener via pynput
# -----------------------------------------------------------------------------

from pynput.mouse import Listener as MouseListener

def on_mouse_click(x, y, button, pressed):
    """
    Called whenever a mouse button is pressed or released.
    We only care about middle-button press.
    """
    if button == Button.middle and pressed:
        handle_middle_click()

def start_mouse_listener():
    listener = MouseListener(on_click=on_mouse_click)
    listener.start()  # runs in a separate thread
    return listener

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    global ocr_region, stop_script

    # 1) Let the user select the OCR region
    ocr_region = select_ocr_region()

    # 2) Initialize keyboard-based hotkeys
    init_keybinds()

    # 3) Start mouse listener to catch middle-button clicks
    mouse_listener = start_mouse_listener()

    # 4) Start the OCR thread
    ocr_thread = threading.Thread(target=ocr_loop, daemon=True)
    ocr_thread.start()

    # 5) Start the scrolling control loop in a separate thread
    scroll_thread = threading.Thread(target=scroll_control_loop, daemon=True)
    scroll_thread.start()

    # 6) Wait for ESC key
    print("Script running. Press ESC to stop.")
    keyboard.wait("esc")

    # 7) Cleanup
    stop_script = True
    print("Stopping script...")
    scroll_thread.join()
    print("Scroll control stopped.")
    # The OCR thread is daemon → ends automatically

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[Info] Script interrupted by user.")
        sys.exit(0)