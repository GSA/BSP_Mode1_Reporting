import os
import boto3
import datetime
from botocore.exceptions import ClientError

# Constants
BUCKET = os.environ['ami_report_s3_bucket']
MGMT_ACCOUNT_ALIAS = os.environ['mgmt_account_alias']
TENANT_ACCOUNTS = os.environ['tenant_accounts'].split(',')
TENANT_NAMES = os.environ['tenant_names'].split(',')
TENANTS = {k:v for k, v in zip(TENANT_NAMES, TENANT_ACCOUNTS)}
KEY_ID = os.environ['ami_report_key_id']
TODAY = datetime.datetime.today().strftime('%Y-%m-%d')
REPORT_NAME = 'ami_report_' + TODAY + '.csv'
CSV_HEADING = ('Tenant,Name,ImageId,State,CreationDate,'
'RootDeviceType,RootDeviceName,SnapshotId')

def create_csv(images):
    csv = CSV_HEADING
    for tenant in sorted(images.keys()):
        for image in images[tenant]:
            csv += ("\r\n" + tenant +
             "," + image['Name'] +
             "," + image['ImageId'] +
             "," + image['State'] +
             "," + image['CreationDate'] +
             "," + image['RootDeviceType'] +
             "," + image['RootDeviceName'] +
             "," + image['BlockDeviceMappings'][0]['Ebs']['SnapshotId'])
    return csv

def get_tenant_ec2_client(sts, name, account):
    role_arn = "arn:aws:iam::" + account + ":role/AMI_Reporting"
    role_session = name + "_session"
    resp = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=role_session
    )
    ec2 = boto3.client(
        'ec2',
        aws_access_key_id=resp['Credentials']['AccessKeyId'],
        aws_secret_access_key=resp['Credentials']['SecretAccessKey'],
        aws_session_token=resp['Credentials']['SessionToken']
    )
    return ec2

def lambda_handler(event, context):
    try:
        images = {}
        # Get Mgmt Account Images
        ec2 = boto3.client('ec2')
        resp = ec2.describe_images(Owners=['self'])
        images[MGMT_ACCOUNT_ALIAS] = resp['Images']

        # Get Tenant Account Images
        sts = boto3.client('sts')
        for name, account in TENANTS.items():
            ec2 = get_tenant_ec2_client(sts, name, account)
            resp = ec2.describe_images(Owners=[account])
            images[name] = resp['Images']

        # Save csv to S3 Bucket
        s3 = boto3.resource('s3')
        s3.Bucket(BUCKET).put_object(
            Key=REPORT_NAME,
            Body=create_csv(images),
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=KEY_ID
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Report Saved: " + BUCKET + "/" + REPORT_NAME)

if __name__ == "__main__":
    json_content = json.loads(open('event.json', 'r').read())
    lambda_handler(json_content, None)
