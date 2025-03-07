import pandas as pd
import pymysql
from sqlalchemy import create_engine
from config import Config

config = Config()


# Use SQLAlchemy for better Pandas integration
def get_db_connection():
    connection_string = f"mysql+pymysql://{config.MYSQL_USER}:{config.MYSQL_PASSWORD}@{config.MYSQL_HOST}/{config.MYSQL_DB}"
    engine = create_engine(connection_string)
    return engine  # SQLAlchemy Engine


def export_training_data():
    engine = get_db_connection()  # Use SQLAlchemy engine
    query = "SELECT component, jtl_article_number FROM jtl_articlenumber_mapping WHERE jtl_article_number IS NOT NULL"

    df = pd.read_sql(query, engine)  # Use engine instead of pymysql connection
    df.to_csv("mapped_components.csv", index=False)

    print("Training data exported successfully!")


if __name__ == '__main__':

    export_training_data()
