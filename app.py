import sys

from flask import Flask, render_template, request, jsonify
import pandas as pd
import joblib
import pymysql
from sqlalchemy import create_engine
from sqlalchemy import text

from config import Config

app = Flask(__name__)
config = Config()

# Load trained AI model
pipeline = joblib.load("jtl_mapper_model.pkl")


# Connect to MySQL using SQLAlchemy
def get_db_connection():
    connection_string = f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}@{config.MYSQL_HOST}/{config.MYSQL_DB}"
    engine = create_engine(connection_string)
    return engine


# Load unmapped components
def load_unmapped_components():
    return pd.read_csv("unmapped_components.csv")


pipeline = joblib.load("jtl_mapper_model.pkl")
fallback_model = joblib.load("fallback_model.pkl")


# Function to auto-generate a JTL article number
def generate_new_jtl(component):
    words = component.split()
    keywords = [word.upper()[:4] for word in words if len(word) > 3]
    base = "_".join(keywords[:3])
    random_number = random.randint(100, 999)  # Avoid duplicates
    return f"JTL_{base}_{random_number}"


@app.route("/predict", methods=["POST"])
def predict_jtl():
    data = request.json
    component = data.get("component")

    if not component:
        return jsonify({"error": "Component description required"}), 400

    try:
        # First, try AI prediction
        predicted_jtl = pipeline.predict([component])[0]
        return jsonify({"component": component, "predicted_jtl": predicted_jtl})
    except:
        # If no match found, use fallback model
        closest_jtl = fallback_model.predict([component])[0]

        if closest_jtl:  # If a close match exists, return it
            return jsonify({"component": component, "predicted_jtl": closest_jtl})

        # Otherwise, generate a completely new JTL article number
        new_jtl = generate_new_jtl(component)
        return jsonify({"component": component, "predicted_jtl": new_jtl})



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/exit")
def app_exit():
    sys.exit(0)




@app.route("/new_mapping", methods=["POST"])
def new_mapping():
    """Add a completely new JTL article number."""
    data = request.json
    component = data["component"]
    jtl_article_number = data["jtl_article_number"]

    if not component or not jtl_article_number:
        return jsonify({"error": "Component and JTL article number are required"}), 400

    # Save to mapped dataset
    df = pd.read_csv("mapped_components.csv")
    new_entry = pd.DataFrame([[component, jtl_article_number]], columns=["component", "jtl_article_number"])
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv("mapped_components.csv", index=False)

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

    return jsonify({"message": "New JTL article number saved!"})



# Get next component to map
@app.route("/next", methods=["GET"])
def get_next_component():
    df = load_unmapped_components()

    if df.empty:
        return jsonify({"message": "No unmapped components left!"}), 404

    # Pick first unmapped component
    component = df.iloc[0]["component"]

    # Predict using AI
    predicted_jtl = pipeline.predict([component])[0]

    return jsonify({"component": component, "predicted_jtl": predicted_jtl})


# Save mapping if user approves
@app.route("/approve", methods=["POST"])
def approve_mapping():
    data = request.json
    component = data["component"]
    jtl_article_number = data["jtl_article_number"]

    # Save to mapped dataset
    df = pd.read_csv("mapped_components.csv")
    new_entry = pd.DataFrame([[component, jtl_article_number]], columns=["component", "jtl_article_number"])
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv("mapped_components.csv", index=False)

    # Remove component from unmapped list
    df_unmapped = load_unmapped_components()
    df_unmapped = df_unmapped[df_unmapped["component"] != component]
    df_unmapped.to_csv("unmapped_components.csv", index=False)

    # Update database using SQLAlchemy text()
    engine = get_db_connection()
    with engine.connect() as conn:
        insert_query = text("""
            INSERT INTO jtl_articlenumber_mapping (component, jtl_article_number)
            VALUES (:component, :jtl_article_number)
            ON DUPLICATE KEY UPDATE jtl_article_number=:jtl_article_number;
        """)

        conn.execute(insert_query, {"component": component, "jtl_article_number": jtl_article_number})
        conn.commit()

    return jsonify({"message": "Mapping approved and saved!"})


# Skip mapping if user rejects it
@app.route("/reject", methods=["POST"])
def reject_mapping():
    data = request.json
    component = data["component"]

    # Remove component from unmapped list
    df_unmapped = load_unmapped_components()
    df_unmapped = df_unmapped[df_unmapped["component"] != component]
    df_unmapped.to_csv("unmapped_components.csv", index=False)

    return jsonify({"message": "Mapping skipped!"})


if __name__ == "__main__":
    app.run(debug=True)
