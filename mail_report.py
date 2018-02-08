import os
import boto3
from botocore.exceptions import ClientError
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

# Constants
KEY_ID = os.environ['ami_report_key_id']

def lambda_handler(event, context):
    ses = boto3.client('ses')
    s3 = boto3.resource('s3')
    s3_key = event['Records'][0]['s3']['object']['key']
    s3_bucket = event['Records'][0]['s3']['bucket']['name']
    file_name = "/tmp/" + s3_key
    to_emails = os.environ['recipients']
    msg = MIMEMultipart()
    msg['From'] = os.environ['sender']
    msg['To'] = to_emails
    AWS_REGION = "us-east-1"
    msg['Subject'] = "Amazon AMI Report"
    CHARSET = "UTF-8"

    # The HTML body of the email.
    BODY_HTML = """<html>
    <head></head>
    <body>
      <h1>AWS Machine Image (AMI) Report</h1>
      <p>Report attached as csv file.</p>
      <p>This email was sent with
        <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
        <a href='https://aws.amazon.com/sdk-for-python/'>
          AWS SDK for Python (Boto)</a>.</p>
    </body>
    </html>
                """
    part = MIMEText(BODY_HTML, 'html', CHARSET)
    msg.attach(part)

    s3.Bucket(s3_bucket).download_file(s3_key, file_name)
    part = MIMEText(open(file_name, "rb").read(), 'csv', CHARSET)
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
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent!")

if __name__ == "__main__":
    json_content = json.loads(open('event.json', 'r').read())
    lambda_handler(json_content, None)
