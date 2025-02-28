import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.neighbors import KNeighborsClassifier

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
