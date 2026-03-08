import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

from google.cloud import storage

logging.getLogger().setLevel(logging.INFO)

EXPORT_FOLDER = "bq-export-security/"
FILE_PREFIX = "baseline_violations_"


def send_csv_email(event, context):

    bucket_name = event.get("bucket")
    file_name = event.get("name")

    if not bucket_name or not file_name:
        logging.warning("Invalid event")
        return

    # Process only our folder
    if not file_name.startswith(EXPORT_FOLDER):
        logging.info("Skipping file outside export folder: %s", file_name)
        return

    # Process only baseline CSV files
    if not file_name.startswith(EXPORT_FOLDER + FILE_PREFIX):
        logging.info("Skipping unrelated file: %s", file_name)
        return

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Find latest file
    blobs = bucket.list_blobs(prefix=EXPORT_FOLDER + FILE_PREFIX)

    latest_blob = None

    for blob in blobs:
        if not blob.name.endswith(".csv"):
            continue

        if latest_blob is None or blob.time_created > latest_blob.time_created:
            latest_blob = blob

    if latest_blob is None:
        logging.info("No matching CSV files found")
        return

    # If triggered file is not the latest, skip
    if latest_blob.name != file_name:
        logging.info("Skipping older file %s. Latest is %s", file_name, latest_blob.name)
        return

    logging.info("Processing latest file: %s", latest_blob.name)

    file_data = latest_blob.download_as_bytes()

    # SMTP Config
    from_email = os.getenv("FROM_EMAIL")
    to_email = os.getenv("TO_EMAIL")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.office365.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    subject = "Baseline Security Findings Report"
    body = "Attached is the latest security findings CSV report."

    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    attachment = MIMEApplication(file_data, _subtype="csv")
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=os.path.basename(latest_blob.name)
    )

    message.attach(attachment)

    server = None

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)

        logging.info("Email sent with latest CSV %s", latest_blob.name)

    except Exception as e:
        logging.error("Error sending email: %s", e)
        raise

    finally:
        if server:
            server.quit()