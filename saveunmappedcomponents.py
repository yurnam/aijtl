import json
import time
import pymysql
import pandas as pd
from config import Config
import requests

config = Config()



# Database connection function
def get_db_connection():
    return pymysql.connect(
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        db=config.MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor
    )
def get_pc_parts_mapping(model):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM pc_parts_mapping WHERE model_name = %s LIMIT 1", (model,))
            result = cursor.fetchone()

    except Exception as e:
        print(f"An error occurred in get_cpu_cooler_type: {e}")
    finally:
        connection.close()
        if result is not None:
            return resultswsw
        else:
            raise Exception(f"No mapping found for model {model}")

# Fetch PCs completed today
def get_today_pcs():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM computers WHERE finished_time LIKE '%2025-03-06%' AND full_disk_info IS NOT null AND customer_serial IS NOT null ")
        return cursor.fetchall()


# Search PC components from local API
def search_computer_with_local_api(customer_serial):
    url = f'http://deploymaster:8082/search?customer_serial={customer_serial}'
    response = requests.get(url)
    return response.json()


# Save unmapped components to CSV for training
def log_unmapped_component(description, customer_serial):
    df = pd.DataFrame([[description, customer_serial]], columns=["component", "customer_serial"])

    try:
        df_existing = pd.read_csv("unmapped_components.csv")
        df = pd.concat([df_existing, df], ignore_index=True)
    except FileNotFoundError:
        pass  # First time running, create a new file

    df.to_csv("unmapped_components.csv", index=False)


# Main Processing
if __name__ == '__main__':
    computers = get_today_pcs()
    comp, pcs = 0, 0

    for computer in computers:
        pcs += 1
        print(f"Processing PC {pcs} of  {len(computers)}")
        customer_serial = computer['customer_serial']



        pc_info = search_computer_with_local_api(customer_serial)

        if pc_info:
            try:
                components = pc_info['components']
                pc_jtl = pc_info['jtl_article_number']
                model_name = pc_info['model_name']
                if pc_jtl in ['None', None, 'null']:
                    print(f"{model_name} has no JTL article number")
                    log_unmapped_component(model_name, customer_serial)
                
            except KeyError:
                print(f"Computer with serial {customer_serial} error DB busy")
                time.sleep(10)
                continue

            for component in components:
                comp += 1
                if component['jtl_article_number'] in ['None', None, 'null']:
                    print(
                        f"Component {component['description']} has no JTL article number for PC with serial {customer_serial}")
                    log_unmapped_component(component['description'], customer_serial)

    print(f"Processed {comp} components for {pcs} PCs")
