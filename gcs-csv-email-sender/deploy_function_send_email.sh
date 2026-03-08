gcloud functions deploy send_csv_email \
--gen2 \
--runtime python311 \
--region us-central1 \
--source=. \
--entry-point send_csv_email \
--trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
--trigger-event-filters="bucket=another-gcs-bucket-in-me2" \
--set-env-vars FROM_EMAIL=no-reply@company.com,TO_EMAIL=recipient@company.com,SMTP_SERVER=smtp.office365.com,SMTP_PORT=587,SMTP_USERNAME=your_username,SMTP_PASSWORD=your_password