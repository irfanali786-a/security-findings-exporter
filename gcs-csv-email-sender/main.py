# main.py
import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

from google.cloud import storage

# Configure logging
logging.getLogger().setLevel(logging.INFO)

# Optional size limit in bytes (e.g., 10 MB). Set to 0 or unset to disable.
MAX_ATTACHMENT_BYTES = int(os.getenv("MAX_ATTACHMENT_BYTES", "10485760"))  # 10 * 1024 * 1024

def send_csv_email(event, context):
    """
    Triggered by a change to a Cloud Storage bucket (finalize/create).
    Expects `event` to include 'bucket' and 'name'.
    Sends the CSV file as an email attachment via SMTP (e.g., Office 365).
    """
    bucket_name = event.get("bucket")
    file_name = event.get("name")

    if not bucket_name or not file_name:
        logging.warning("Event missing 'bucket' or 'name'. Event: %s", event)
        return

    # Only process CSV files
    if not file_name.lower().endswith(".csv"):
        logging.info("Skipping non-CSV object: %s", file_name)
        return

    # Load SMTP config from environment
    from_email = os.getenv("FROM_EMAIL")             # e.g. 'no-reply@company.com'
    to_email = os.getenv("TO_EMAIL")                 # e.g. 'recipient@company.com'
    smtp_server = os.getenv("SMTP_SERVER", "smtp.office365.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    subject = os.getenv("EMAIL_SUBJECT", "Baseline_Security Findings Report")
    body = os.getenv("EMAIL_BODY", "Attached is the latest security findings CSV report.")

    # Validate mandatory configuration
    missing = [k for k, v in {
        "FROM_EMAIL": from_email,
        "TO_EMAIL": to_email,
        "SMTP_USERNAME": smtp_username,
        "SMTP_PASSWORD": smtp_password
    }.items() if not v]
    if missing:
        raise ValueError(f"Required environment variables missing: {', '.join(missing)}")

    # Download the object
    storage_client = storage.Client()
    blob = storage_client.bucket(bucket_name).blob(file_name)

    # Optional size check before download
    blob.reload()  # fetch metadata including size
    size_bytes = blob.size or 0
    if MAX_ATTACHMENT_BYTES and size_bytes > MAX_ATTACHMENT_BYTES:
        logging.warning(
            "File %s is %d bytes, exceeding MAX_ATTACHMENT_BYTES=%d; skipping email.",
            file_name, size_bytes, MAX_ATTACHMENT_BYTES
        )
        return

    file_data = blob.download_as_bytes()

    # Build MIME message
    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # Attach CSV (content-type: text/csv)
    attachment = MIMEApplication(file_data, _subtype="csv")
    attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(file_name))
    message.attach(attachment)

    # Send via SMTP (STARTTLS)
    server = None
    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)
        logging.info("Email sent to %s with attachment %s (%d bytes).", to_email, file_name, len(file_data))
    except smtplib.SMTPException as e:
        logging.error("SMTP error sending email: %s", e)
        raise
    except Exception as e:
        logging.error("Unexpected error sending email: %s", e)
        raise
    finally:
        try:
            if server:
                server.quit()
        except Exception:
            pass