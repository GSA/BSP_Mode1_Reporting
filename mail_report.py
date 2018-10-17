"""
Lambda function for creating emailing daily AMI Report

Sends a CSV report from an S3 bucket as an attachment to a distribution list
specified in the `recipients` environment variable.
"""
import os
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import boto3
from botocore.exceptions import ClientError

# Constants
KEY_ID = os.environ['ami_report_key_id']
TODAY = datetime.datetime.today().strftime('%Y-%m-%d')

def get_header(key):
    """Returns eMail header based on file name"""
    if key.startswith('ami_report_'):
        return 'BSP Mode1 AWS Machine Image (AMI) Report'
    if key.startswith('snapshot_report_'):
        return 'BSP Mode1 Snapshot Report'
    return 'BSP Mode1 AWS Inventory Report from Lambda Function - ' + key

def get_subject(key):
    """Returns eMail subject based on file name"""
    if key.startswith('ami_report_'):
        return "BSP Mode1 AMI Report - " + TODAY
    if key.startswith('snapshot_report_'):
        return "BSP Mode1 Snapshot Report - " + TODAY
    return "BSP Mode1 Inventory Report - " + key

def mail_report(event):
    """Handler function for Lambda function to mail AMI Report"""
    ses = boto3.client('ses')
    s3_res = boto3.resource('s3')
    s3_key = event['Records'][0]['s3']['object']['key']
    s3_bucket = event['Records'][0]['s3']['bucket']['name']
    file_name = "/tmp/" + s3_key
    to_emails = os.environ['recipients']
    header = get_header(s3_key)
    msg = MIMEMultipart()
    msg['From'] = os.environ['sender']
    msg['To'] = to_emails
    msg['Subject'] = get_subject(s3_key)
    char_set = "UTF-8"

    # The HTML body of the email.
    body_html = """<html>
    <head></head>
    <body>
      <h1>{0}</h1>
      <p>Report attached as csv file.</p>
      <p>This email was sent with
        <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
        <a href='https://aws.amazon.com/sdk-for-python/'>
          AWS SDK for Python (Boto)</a>.</p>
    </body>
    </html>
                """.format(header)
    part = MIMEText(body_html, 'html', char_set)
    msg.attach(part)

    s3_res.Bucket(s3_bucket).download_file(s3_key, file_name)
    part = MIMEText(open(file_name, "rb").read(), 'csv', char_set)
    part.add_header('Content-Disposition', 'attachment', filename=s3_key)
    msg.attach(part)

    # Try to send the email.
    try:
        #Provide the contents of the email.
        ses.send_raw_email(
            RawMessage={
                'Data': msg.as_string(),
            },
            Source=msg['From'],
            Destinations=to_emails.split(",")
        )
    # Display an error if something goes wrong.
    except ClientError as err:
        print(err.response['Error']['Message'])
    else:
        print("Email sent!")

def lambda_handler(event, context):
    """Handler function for Lambda function to determine if CSV"""
    del context # Unused
    if event['Records'][0]['s3']['object']['key'].endswith('.csv'):
        mail_report(event)
    else:
        print(event['Records'][0]['s3']['object']['key'] + " not a CSV file")

if __name__ == "__main__":
    JSON_CONTENT = json.loads(open('event.json', 'r').read())
    lambda_handler(JSON_CONTENT, None)
