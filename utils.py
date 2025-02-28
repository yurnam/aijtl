import json
import time
import pymysql
import pandas as pd
from config import Config
import requests
from sqlalchemy import create_engine
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.neighbors import KNeighborsClassifier
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
import random


def search_computer_with_local_api(customer_serial):
    url = f'http://deploymaster:8082/search?customer_serial={customer_serial}'
    response = requests.get(url)
    return response.json()


def log_unmapped_component(description, customer_serial):
    df = pd.DataFrame([[description, customer_serial]], columns=["component", "customer_serial"])

    try:
        df_existing = pd.read_csv("unmapped_components.csv")
        df = pd.concat([df_existing, df], ignore_index=True)
    except FileNotFoundError:
        pass  # First time running, create a new file

    df.to_csv("unmapped_components.csv", index=False)


class UnmappedComponentsSaver:
    def __init__(self):
        self.config = Config()

        computers = self.get_today_pcs()
        comp, pcs = 0, 0

        for computer in computers:
            pcs += 1
            print(f"Processing PC {pcs} of  {len(computers)}")
            customer_serial = computer['customer_serial']
            pc_info = search_computer_with_local_api(customer_serial)

            if pc_info:
                try:
                    components = pc_info['components']
                except KeyError:
                    print(f"Computer with serial {customer_serial} error DB busy")
                    time.sleep(10)
                    continue

                for component in components:
                    comp += 1
                    if component['jtl_article_number'] in ['None', None]:
                        print(
                            f"Component {component['description']} has no JTL article number for PC with serial {customer_serial}")
                        log_unmapped_component(component['description'], customer_serial)

        print(f"Processed {comp} components for {pcs} PCs")

    def get_db_connection(self):
        return pymysql.connect(
            host=self.config.MYSQL_HOST,
            user=self.config.MYSQL_USER,
            password=self.config.MYSQL_PASSWORD,
            db=self.config.MYSQL_DB,
            cursorclass=pymysql.cursors.DictCursor
        )

    def get_today_pcs(self):
        connection = self.get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM computers WHERE finished_time LIKE '%2025-02-07%' AND full_disk_info IS NOT null AND customer_serial IS NOT null and status = 'Fertig' ")
            return cursor.fetchall()


class MappedComponentsSaver:

    def __init__(self):
        self.config = Config()
        self.export_training_data()

    def get_db_connection(self):
        config = self.config
        connection_string = f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}@{config.MYSQL_HOST}/{config.MYSQL_DB}"
        engine = create_engine(connection_string)
        return engine  # SQLAlchemy Engine

    def export_training_data(self):
        engine = self.get_db_connection()  # Use SQLAlchemy engine
        query = "SELECT component, jtl_article_number FROM jtl_articlenumber_mapping WHERE jtl_article_number IS NOT NULL"

        df = pd.read_sql(query, engine)  # Use engine instead of pymysql connection
        df.to_csv("mapped_components.csv", index=False)

        print("Training data exported successfully!")


class Model:

    def initial_train(self):
        # Load dataset
        df = pd.read_csv("mapped_components.csv").dropna()

        X = df["component"]
        y = df["jtl_article_number"]

        # Train a new AI model
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('clf', RandomForestClassifier(n_estimators=200, random_state=42))
        ])

        pipeline.fit(X, y)

        # Train an additional model for unseen components
        fallback_model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('clf', KNeighborsClassifier(n_neighbors=3))  # Finds closest known JTL
        ])

        fallback_model.fit(X, y)

        # Save models
        joblib.dump(pipeline, "jtl_mapper_model.pkl")
        joblib.dump(fallback_model, "fallback_model.pkl")

        print("Models trained successfully!")


    def retrain(self):
        df = pd.read_csv("mapped_components.csv").dropna()

        if df.empty:
            print("No data found in mapped_components.csv! Training aborted.")
            exit()

        X = df["component"]
        y = df["jtl_article_number"]

        # **Train the Primary Model (RandomForest)**
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('clf', RandomForestClassifier(n_estimators=200, random_state=42))
        ])

        pipeline.fit(X, y)

        # **Train a Fallback Model for Unseen Components (KNN)**
        fallback_model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('clf', KNeighborsClassifier(n_neighbors=3))  # Finds closest known JTL
        ])

        fallback_model.fit(X, y)

        # Save models
        joblib.dump(pipeline, "jtl_mapper_model.pkl")
        joblib.dump(fallback_model, "fallback_model.pkl")

        print("Models retrained successfully!")

        # **Function to Auto-Generate a Unique JTL Article Number**
        def generate_unique_jtl(component, existing_jtl_list):
            words = component.split()
            keywords = [word.upper()[:4] for word in words if len(word) > 3]
            base = "_".join(keywords[:3])

            # Generate a random number and ensure uniqueness
            while True:
                random_number = random.randint(100, 999)
                new_jtl = f"JTL_{base}_{random_number}"
                if new_jtl not in existing_jtl_list:
                    return new_jtl

        # **Enhancing the Dataset with AI-Generated JTL Codes**
        existing_jtl_list = set(y)

        df_unmapped = pd.read_csv("unmapped_components.csv")

        if not df_unmapped.empty:
            for index, row in df_unmapped.iterrows():
                component = row["component"]

                # Use fallback model to get a close match
                try:
                    predicted_jtl = fallback_model.predict([component])[0]
                except:
                    predicted_jtl = generate_unique_jtl(component, existing_jtl_list)

                # Add new mapping
                new_entry = pd.DataFrame([[component, predicted_jtl]], columns=["component", "jtl_article_number"])
                df = pd.concat([df, new_entry], ignore_index=True)
                existing_jtl_list.add(predicted_jtl)

            # Save updated training data
            df.to_csv("mapped_components.csv", index=False)
            print("Added AI-generated mappings and updated dataset!")

        print("Retraining complete.")
