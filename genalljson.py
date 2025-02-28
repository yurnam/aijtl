import json
import time
import pymysql
import pandas as pd
import requests
from config import Config

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


# Fetch PCs completed today
def get_today_pcs():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT model_name, customer_serial FROM computers "
            "WHERE finished_time LIKE '%2025-02-13%'"
            "AND full_disk_info IS NOT NULL "
            "AND customer_serial IS NOT NULL "
            "AND status = 'Fertig'"
        )
        return cursor.fetchall()


# Trigger report generation for a PC via API
def report_pc(customer_serial, model_name):
    url = "http://deploymaster:8082/report_by_serial"
    data = {"model_name": model_name, "customer_serial": customer_serial}

    try:
        response = requests.post(url, json=data)
        response_data = response.json()

        if response.status_code == 200:
            print(f"Report generated successfully for {customer_serial}")
        else:
            print(f"Failed to generate report for {customer_serial}: {response_data.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"Error reporting PC {customer_serial}: {e}")


# Process all today's PCs and trigger reports
if __name__ == '__main__':
    computers = get_today_pcs()
    total_pcs = len(computers)

    if total_pcs == 0:
        print("No PCs found for today.")
    else:
        print(f"Found {total_pcs} PCs to process.")

    for idx, computer in enumerate(computers, start=1):
        model_name = computer['model_name']
        customer_serial = computer['customer_serial']

        print(f"Processing PC {idx} of {total_pcs} - Serial: {customer_serial}, Model: {model_name}")
        try:
            report_pc(customer_serial, model_name)
            time.sleep(.5)
        except Exception as e:
            print(f"Error processing PC {customer_serial}")

    print(f"Completed processing {total_pcs} PCs.")
