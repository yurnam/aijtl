import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
import random


def retrain():
    # Load updated data
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

    # **Update Dataset with AI-Generated Mappings**

    existing_jtl_list = set(y)

    df_unmapped = pd.read_csv("unmapped_components.csv")

    if not df_unmapped.empty:
        for index, row in df_unmapped.iterrows():
            component = row["component"]

            # Use fallback model to get a close match
            try:
                predicted_jtl = fallback_model.predict([component])[0]
            except Exception as e:
                print(f"Error predicting JTL for {component}: {e}")
                predicted_jtl = generate_unique_jtl(component, existing_jtl_list)

            # Add new mapping
            new_entry = pd.DataFrame([[component, predicted_jtl]], columns=["component", "jtl_article_number"])
            df = pd.concat([df, new_entry], ignore_index=True)
            existing_jtl_list.add(predicted_jtl)

        # Save updated training data
        df.to_csv("mapped_components.csv", index=False)
        print("Added AI-generated mappings and updated dataset!")

    print("Retraining complete.")
