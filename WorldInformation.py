from airflow import DAG
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
from pandas import Timestamp

import yfinance as yf
import pandas as pd
import logging
import requests


def get_Redshift_connection(autocommit=True):
    hook = PostgresHook(postgres_conn_id='redshift_dev_db')
    conn = hook.get_conn()
    conn.autocommit = autocommit
    return conn.cursor()


@task
def get_world_information():
    url = "https://restcountries.com/v3/all"
    response = requests.get(url)
    
    data = response.json()
    records = []
    
    for country in data:
        record = {
            "country" : country["name"]["official"],
            "population" : country["population"],
            "area" : country["area"]
        }
        records.append(record)
    
    return records

@task
def load(schema, table, records):
    logging.info("load started")
    cur = get_Redshift_connection()
    try:
        cur.execute("BEGIN;")
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{table};")
        cur.execute(f"""
CREATE TABLE {schema}.{table} (
    country varchar(200),
    population bigint,
    area bigint
);""")
        # DELETE FROM을 먼저 수행 -> FULL REFRESH을 하는 형태
        for r in records:
            sql = f"INSERT INTO {schema}.{table} VALUES ('{r['country']}', {r['population']}, {r['area']});"
            print(sql)
            cur.execute(sql)
        cur.execute("COMMIT;")   # cur.execute("END;")
    except Exception as error:
        print(error)
        cur.execute("ROLLBACK;")
        raise

    logging.info("load done")


with DAG(
    dag_id = 'UpdateWorldInfo',
    start_date = datetime(2023,5,30),
    catchup=False,
    tags=['API'],
    schedule = '30 6 * * 6'
) as dag:

    results = get_world_information()
    load("jwa4610", "world_information", results)