from google.cloud import bigquery
from google.cloud import storage
import csv
import io
from datetime import datetime


def export_bq_to_csv(request):

    # Configuration
    project_id = "securing-gcp"
    dataset_id = "security_monitoring"
    table_id = "baseline_violations"
    bucket_name = "another-gcs-bucket-in-me2"
    folder_path = "bq-export-security"

    bq_client = bigquery.Client(project=project_id)
    storage_client = storage.Client()

    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    # Query BigQuery table
    query = f"""
    SELECT *
    FROM `{table_ref}`
    """

    query_job = bq_client.query(query)
    rows = query_job.result()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    headers = [field.name for field in rows.schema]
    writer.writerow(headers)

    # Write data rows
    for row in rows:
        writer.writerow(list(row.values()))

    # Create file name with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"{folder_path}/baseline_violations_{timestamp}.csv"

    # Upload to GCS
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    blob.upload_from_string(
        output.getvalue(),
        content_type="text/csv"
    )

    return f"CSV exported to gs://{bucket_name}/{file_name}"


if __name__ == "__main__":
    result = export_bq_to_csv(None)
    print(result)
