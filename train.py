import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import joblib

# Load mapped data
df = pd.read_csv("mapped_components.csv")

# Drop any null values
df.dropna(inplace=True)

# Split into features (X) and target (y)
X = df["component"]  # Component descriptions
y = df["jtl_article_number"]  # JTL mapping

# Split into training & testing datasets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Define TF-IDF + Random Forest Pipeline
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),  # Convert text to numerical
    ('clf', RandomForestClassifier(n_estimators=100, random_state=42))  # Train classifier
])

# Train model
pipeline.fit(X_train, y_train)

# Evaluate model
accuracy = pipeline.score(X_test, y_test)
print(f"Model Accuracy: {accuracy:.2f}")

# Save trained model
joblib.dump(pipeline, "jtl_mapper_model.pkl")
print("Model saved successfully!")
