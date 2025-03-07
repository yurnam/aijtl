import pygame
import requests
import time
import threading
import tkinter as tk
from tkinter import ttk

# Flask server URL
FLASK_SERVER = "http://127.0.0.1:5000"

# Initialize pygame for PS4 Controller
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No controller detected! Make sure your PS4 controller is connected via Bluetooth.")
    joystick = None
else:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Connected to: {joystick.get_name()}")

current_mapping = None

def get_next_mapping():
    """Fetch the next unmapped component from Flask server"""
    response = requests.get(f"{FLASK_SERVER}/next")
    if response.status_code == 200:
        return response.json()
    return None

def predict_new_jtl(component):
    """Request AI to generate a JTL article number for unseen components"""
    response = requests.post(f"{FLASK_SERVER}/predict", json={"component": component})
    if response.status_code == 200:
        return response.json()["predicted_jtl"]
    return "UNKNOWN"

def approve_mapping():
    """Approve the current mapping"""
    global current_mapping
    if current_mapping:
        requests.post(f"{FLASK_SERVER}/approve", json={
            "component": current_mapping["component"],
            "jtl_article_number": current_mapping["predicted_jtl"]
        })
        update_status(f"✅ Approved: {current_mapping['component']} → {current_mapping['predicted_jtl']}")
        load_next_mapping()


def kill_app_server():
    """Kill the Flask server"""
    response = requests.get(f"{FLASK_SERVER}/exit")
    if response.status_code == 200:
        print("Server killed successfully!")
    else:
        print("Failed to kill server!")

def reject_mapping():
    """Reject the current mapping"""
    global current_mapping
    if current_mapping:
        requests.post(f"{FLASK_SERVER}/reject", json={"component": current_mapping["component"]})
        update_status(f"❌ Skipped: {current_mapping['component']}")
        load_next_mapping()

def create_new_jtl():
    """Create a new JTL article number manually or via AI"""
    global current_mapping
    if current_mapping:
        new_jtl = new_jtl_entry.get().strip()
        if not new_jtl:  # If the user does not enter anything, auto-generate
            new_jtl = predict_new_jtl(current_mapping["component"])
            new_jtl_entry.insert(0, new_jtl)  # Suggest auto-generated JTL

        requests.post(f"{FLASK_SERVER}/new_mapping", json={
            "component": current_mapping["component"],
            "jtl_article_number": new_jtl
        })
        update_status(f"🆕 New JTL Created: {current_mapping['component']} → {new_jtl}")
        load_next_mapping()

def load_next_mapping():
    """Load the next component mapping"""
    global current_mapping
    current_mapping = get_next_mapping()
    if current_mapping:
        component_label.config(text=f"Component: {current_mapping['component']}")
        predicted_label.config(text=f"Predicted JTL: {current_mapping['predicted_jtl']}")
        new_jtl_entry.delete(0, tk.END)
    else:
        component_label.config(text="No more unmapped components!")
        predicted_label.config(text="")
        approve_button.config(state=tk.DISABLED)
        reject_button.config(state=tk.DISABLED)
        new_jtl_button.config(state=tk.DISABLED)

def update_status(message):
    """Update the status label in the GUI"""
    status_label.config(text=message)
    root.update_idletasks()

# 🎮 PS4 Controller Listener (Runs in Background)
def ps4_listener():
    """Listen for PS4 controller inputs"""
    while True:
        if joystick:
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 7:  # R2 → Approve
                        approve_mapping()
                    elif event.button == 6:  # L2 → Reject
                        reject_mapping()
                    elif event.button == 9:  # Options Button → Exit
                        print("Exiting...")
                        root.quit()
                        return
        time.sleep(0.1)


if __name__ == '__main__':
    """Run the GUI"""
# Create GUI Window
    root = tk.Tk()
    root.title("AI JTL Mapper")
    root.geometry("900x350")

    # UI Components
    frame = ttk.Frame(root, padding=20)
    frame.pack(expand=True)

    component_label = ttk.Label(frame, text="Loading component...", font=("Arial", 12))
    component_label.pack(pady=10)

    predicted_label = ttk.Label(frame, text="", font=("Arial", 10, "bold"))
    predicted_label.pack(pady=5)

    status_label = ttk.Label(frame, text="", font=("Arial", 10))
    status_label.pack(pady=5)

    approve_button = ttk.Button(frame, text="✅ Approve", command=approve_mapping)
    approve_button.pack(side=tk.RIGHT, padx=10)

    reject_button = ttk.Button(frame, text="❌ Reject", command=reject_mapping)
    reject_button.pack(side=tk.LEFT, padx=10)

    kill_button = ttk.Button(frame, text="🔴 Kill Server", command=kill_app_server)
    kill_button.pack(side=tk.LEFT, padx=10)


    new_jtl_label = ttk.Label(frame, text="Enter new JTL Article Number:")
    new_jtl_label.pack(pady=5)

    new_jtl_entry = ttk.Entry(frame, width=30)
    new_jtl_entry.pack(pady=5)

    new_jtl_button = ttk.Button(frame, text="🆕 Create New JTL", command=create_new_jtl)
    new_jtl_button.pack(pady=5)

    # Start GUI & Controller Thread
    load_next_mapping()
    controller_thread = threading.Thread(target=ps4_listener, daemon=True)
    controller_thread.start()

    root.mainloop()


