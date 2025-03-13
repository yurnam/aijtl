
class Config:
    MYSQL_HOST = 'digikex.com'  # Your MySQL host
    MYSQL_USER = 'root'       # Your MySQL username
    MYSQL_PASSWORD = 'saDigiKEX2021#!'  # Your MySQL password
    MYSQL_DB = 'lager'  # Your MySQL database name
    MAIN_MODEL_FILE = "resources/jtl_mapper_model.pkl"
    FALLBACK_MODEL_FILE = "resources/fallback_model.pkl"
    UNMAPPED_COMPONENTS_FILE = "resources/unmapped_components.csv"
    MAPPED_COMPONENTS_FILE = "resources/mapped_components.csv"