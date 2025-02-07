import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

# Load updated data
df = pd.read_csv("mapped_components.csv").dropna()

X = df["component"]
y = df["jtl_article_number"]

# Train a new model
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
    ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
])

pipeline.fit(X, y)

# Save the updated model
joblib.dump(pipeline, "jtl_mapper_model.pkl")

print("Model retrained successfully!")
