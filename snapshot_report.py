"""
Lambda function for creating daily Snapshot Report

Creates a CSV report of all snapshots in each account listed
in the `tenant_accounts` environment variable and saves it to the S3 bucket
specified in the `snapshot_report_s3_bucket` environment variable
"""
import os
import datetime
import json
from botocore.exceptions import ClientError
import boto3

# Constants
BUCKET = os.environ['snapshot_report_s3_bucket']
MGMT_ACCOUNT_ALIAS = os.environ['mgmt_account_alias']
MGMT_ACCOUNT_ID = os.environ['mgmt_account']
TENANT_ACCOUNTS = os.environ['tenant_accounts'].split(',')
TENANT_NAMES = os.environ['tenant_names'].split(',')
TENANTS = {k:v for k, v in zip(TENANT_NAMES, TENANT_ACCOUNTS)}
KEY_ID = os.environ['snapshot_report_key_id']
TODAY = datetime.datetime.today().strftime('%Y-%m-%d')
REPORT_NAME = 'snapshot_report_' + TODAY + '.csv'
CSV_HEADING = ('Tenant,Name,SnapshotId,Description,State,StartTime,'
               'VolumeId,VolumeSize,SnapshotId')
EMPTY_TAGS_DICT = {
    'Name': '',
    'SnapshotRetentionPeriod': '',
    'CostControl': '',
    'SnapshotSet': '',
    'POC': ''
}

def tags_to_dict(tags):
    """Converts array of Key, Value objects into a dictionary"""
    tags_dict = EMPTY_TAGS_DICT
    for tag in tags:
        tags_dict[tag['Key']] = tag['Value']
    return tags_dict

def create_csv(snapshots):
    """Converts the snapshot info into a CSV string"""
    csv = CSV_HEADING
    for tenant in sorted(snapshots.keys()):
        for snapshot in snapshots[tenant]:
            if "Tags" in snapshot:
                tags_dict = tags_to_dict(snapshot['Tags'])
            else:
                tags_dict = EMPTY_TAGS_DICT
            csv += ("\r\n" + tenant +
                    "," + tags_dict['Name'] +
                    "," + snapshot['SnapshotId'] +
                    "," + snapshot['Description'] +
                    "," + snapshot['State'] +
                    "," + snapshot['StartTime'].strftime("%B %d, %Y") +
                    "," + snapshot['VolumeId'] +
                    "," + str(snapshot['VolumeSize']) +
                    "," + tags_dict['SnapshotRetentionPeriod'] +
                    "," + tags_dict['CostControl'] +
                    "," + tags_dict['SnapshotSet'] +
                    "," + tags_dict['POC'])
    return csv

def get_tenant_ec2_client(sts, name, account):
    """Gets AWS API EC2 client for the AWS account"""
    role_arn = "arn:aws:iam::" + account + ":role/snapshot-reporting"
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
    """Lambda function handler to create BSP Snapshot Report"""
    del context, event # Unused
    try:
        snapshots = {}
        # Get Mgmt Account Snapshots
        ec2 = boto3.client('ec2')
        resp = ec2.describe_snapshots(OwnerIds=[MGMT_ACCOUNT_ID])
        snapshots[MGMT_ACCOUNT_ALIAS] = resp['Snapshots']

        # Get Tenant Account Snapshots
        sts = boto3.client('sts')
        for name, account in TENANTS.items():
            ec2 = get_tenant_ec2_client(sts, name, account)
            resp = ec2.describe_snapshots(OwnerIds=[account])
            snapshots[name] = resp['Snapshots']

        # Save csv to S3 Bucket
        s3_res = boto3.resource('s3')
        s3_res.Bucket(BUCKET).put_object(
            Key=REPORT_NAME,
            Body=create_csv(snapshots),
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=KEY_ID,
            StorageClass='REDUCED_REDUNDANCY'
        )
    except ClientError as err:
        print(err.response['Error']['Message'])
    else:
        print("Report Saved: " + BUCKET + "/" + REPORT_NAME)

if __name__ == "__main__":
    JSON_CONTENT = json.loads(open('event.json', 'r').read())
    lambda_handler(JSON_CONTENT, None)
