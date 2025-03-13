import pygame
import requests
import time
import threading
import tkinter as tk
from tkinter import ttk
import pandas as pd
import joblib
import pymysql
from sqlalchemy import create_engine
from sqlalchemy import text
from config import Config
import saveunmappedcomponents
import savemappedcomponents
import retrain

config = Config()

def get_db_connection():
    connection_string = f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}@{config.MYSQL_HOST}/{config.MYSQL_DB}"
    engine = create_engine(connection_string)
    return engine

def load_unmapped_components():
    return pd.read_csv(config.UNMAPPED_COMPONENTS_FILE)

pipeline = joblib.load(config.MAIN_MODEL_FILE)
fallback_model = joblib.load(config.FALLBACK_MODEL_FILE)


# Function to auto-generate a JTL article number
def generate_new_jtl(component):
    words = component.split()
    keywords = [word.upper()[:4] for word in words if len(word) > 3]
    base = "_".join(keywords[:3])
    random_number = random.randint(100, 999)  # Avoid duplicates
    return f"JTL_{base}_{random_number}"


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

    df = load_unmapped_components()

    if df.empty:
        return None

    # Pick first unmapped component
    component = df.iloc[0]["component"]

    # Predict using AI
    predicted_jtl = pipeline.predict([component])[0]

    return {"component": component, "predicted_jtl": predicted_jtl}



def predict_new_jtl(component):
    """Request AI to generate a JTL article number for unseen components"""
    try:
        predicted_jtl = pipeline.predict([component])[0]
        return predicted_jtl

    except:
        closest_jtl = fallback_model.predict([component])[0]

        if closest_jtl:
            return closest_jtl

        new_jtl = generate_new_jtl(component)
        return new_jtl


def approve_mapping():
    """Approve the current mapping"""
    global current_mapping
    if current_mapping:

        component = current_mapping["component"]
        jtl_article_number = current_mapping["predicted_jtl"]
        df = pd.read_csv(config.MAPPED_COMPONENTS_FILE)
        new_entry = pd.DataFrame([[component, jtl_article_number]], columns=["component", "jtl_article_number"])
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_csv(config.MAPPED_COMPONENTS_FILE, index=False)

        df_unmapped = load_unmapped_components()
        df_unmapped = df_unmapped[df_unmapped["component"] != component]
        df_unmapped.to_csv(config.UNMAPPED_COMPONENTS_FILE, index=False)

        engine = get_db_connection()
        with engine.connect() as conn:
            insert_query = text("""
                INSERT INTO jtl_articlenumber_mapping (component, jtl_article_number)
                VALUES (:component, :jtl_article_number)
                ON DUPLICATE KEY UPDATE jtl_article_number=:jtl_article_number;
            """)

            conn.execute(insert_query, {"component": component, "jtl_article_number": jtl_article_number})
            conn.commit()


        update_status(f"✅ Approved: {current_mapping['component']} → {current_mapping['predicted_jtl']}")
        load_next_mapping()


def kill_app_server():
    exit()

def reject_mapping():
    """Reject the current mapping"""
    global current_mapping
    if current_mapping:
        component = current_mapping["component"]
        df_unmapped = load_unmapped_components()
        df_unmapped = df_unmapped[df_unmapped["component"] != component]
        df_unmapped.to_csv(config.UNMAPPED_COMPONENTS_FILE, index=False)

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

        component = current_mapping["component"]
        jtl_article_number = new_jtl


        if not component or not jtl_article_number:
            return jsonify({"error": "Component and JTL article number are required"}), 400

            # Save to mapped dataset
        df = pd.read_csv(config.MAPPED_COMPONENTS_FILE)
        new_entry = pd.DataFrame([[component, jtl_article_number]], columns=["component", "jtl_article_number"])
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_csv(config.MAPPED_COMPONENTS_FILE, index=False)

        # Update database
        engine = get_db_connection()
        with engine.connect() as conn:
            insert_query = text("""
                   INSERT INTO jtl_articlenumber_mapping (component, jtl_article_number)
                   VALUES (:component, :jtl_article_number)
                   ON DUPLICATE KEY UPDATE jtl_article_number=:jtl_article_number;
               """)
            conn.execute(insert_query, {"component": component, "jtl_article_number": jtl_article_number})
            conn.commit()



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
    savemappedcomponents.export_training_data()
    retrain.retrain()
    saveunmappedcomponents.process_computers_from_date('2025-03-12')


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

    kill_button = ttk.Button(frame, text="🔴 Exit", command=kill_app_server)
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


