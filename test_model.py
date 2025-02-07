import joblib
import pandas as pd

# Load the trained model
pipeline = joblib.load("jtl_mapper_model.pkl")

# Load unmapped components
unmapped_df = pd.read_csv("unmapped_components.csv")

# Predict JTL article numbers
unmapped_df["predicted_jtl_article_number"] = pipeline.predict(unmapped_df["component"])

# Save results
unmapped_df.to_csv("predicted_mappings.csv", index=False)

print("Predictions saved successfully!")
