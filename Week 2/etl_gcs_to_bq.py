from pathlib import Path
import pandas as pd
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket
from prefect_gcp import GcpCredentials


@task(log_prints=True, retries=3)
def extract_from_gcs(color: str, year: int, month: int)-> pd.DataFrame:
    """Download trip data from GCS"""
    gcs_path = f"data/{color}/{color}_tripdata_{year}-{month:02}.parquet"
    gcs_block = GcsBucket.load("zoom-gcs")
    gcs_block.get_directory(from_path=gcs_path, local_path=f"./data/")
    df = pd.read_parquet(f"./data/{gcs_path}")

    return df




@task(log_prints=True, retries=3)
def write_bq(df: pd.DataFrame) -> None:
    """Write DataFrame to BiqQuery"""

    gcp_credentials_block = GcpCredentials.load("zoom-gcs-credns")

    df.to_gbq(
        destination_table="dezoomcampbq.rides",
        project_id="dezoom2023",
        credentials=gcp_credentials_block.get_credentials_from_service_account(),
        chunksize=500_000,
        if_exists="append",
    )


@flow(log_prints=True)
def etl_gcs_to_bq(year: int, month: int, color: str) -> None:
    """Main ETL flow to load data into Big Query"""
    color = color
    year = year
    month = month

    df = extract_from_gcs(color, year, month)
    #df = transform(path)
    write_bq(df)



@flow(log_prints=True)
def etl_gcs_to_bq_parent_flow(
    months: list[int] = [2, 3], year: int = 2019, color: str = "yellow"
):
    for month in months:
        etl_gcs_to_bq(year, month, color)


if __name__ == "__main__":
    color = "yellow"
    months = [ 2, 3]
    year = 2019
    etl_gcs_to_bq_parent_flow(months, year, color)