from datetime import datetime
from airflow import DAG  # type: ignore
try:
    from airflow.providers.standard.operators.bash import BashOperator  # type: ignore
except ImportError:
    from airflow.operators.bash import BashOperator  # type: ignore


with DAG(
    dag_id="cricket_pipeline",
    start_date=datetime(2026, 9, 1),
    schedule=None,
    catchup=False,
    tags=["cricket", "scraping", "data_engineering"],
) as dag:

    # Step 1: Discover all international teams and player URLs
    step1_scraping = BashOperator(
        task_id="step1_scraping",
        bash_command="""
            set -e
            mkdir -p /opt/airflow/Data
            cd /opt/airflow
            xvfb-run -a python /opt/airflow/dags/step1.py
        """,
    )

    # Step 2: Scrape detailed player stats and career records
    step2_processing = BashOperator(
        task_id="step2_processing",
        bash_command="""
            set -e
            cd /opt/airflow
            xvfb-run -a python /opt/airflow/dags/step2.py
        """,
    )

    # # Step 3: Import players, matches, and ball-by-ball deliveries into PostgreSQL
    # step3_import = BashOperator(
    #     task_id="step3_import",
    #     bash_command="""
    #         set -e
    #         cd /opt/airflow
    #         python /opt/airflow/dags/step3.py
    #     """,
    # )

    step1_scraping >> step2_processing