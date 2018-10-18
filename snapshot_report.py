"""
Lambda function for creating daily Snapshot Report

Creates a CSV report of all snapshots in each account listed
in the `tenant_accounts` environment variable and saves it to the S3 bucket
specified in the `snapshot_report_s3_bucket` environment variable
"""
import os
import datetime
import json
import re
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
CSV_HEADING = ('Tenant,Name,SnapshotId,Description,State,StartTime,' +
               'VolumeId,VolumeSize,ImageId,ImageStatus,' +
               'SnapshotRetionPeriod,CostControl,SnapshotSet,POC')
EMPTY_TAGS_DICT = {
    'Name': '',
    'SnapshotRetentionPeriod': '',
    'CostControl': '',
    'SnapshotSet': '',
    'POC': ''
}

def tags_to_dict(tags):
    """Converts array of Key, Value objects into a dictionary"""
    t_dict = {}
    t_dict.update(EMPTY_TAGS_DICT)
    for tag in tags:
        t_dict[tag['Key']] = tag['Value']
    return t_dict

def create_csv(snapshots):
    """Converts the snapshot info into a CSV string"""
    csv = CSV_HEADING
    for tenant in sorted(snapshots.keys()):
        for snapshot in snapshots[tenant]:
            tags_dict = {}
            tags_dict.update(EMPTY_TAGS_DICT)
            if "Tags" in snapshot:
                tags_dict.update(tags_to_dict(snapshot['Tags']))
            csv += ("\r\n" + tenant +
                    "," + tags_dict['Name'] +
                    "," + snapshot['SnapshotId'] +
                    "," + snapshot['Description'] +
                    "," + snapshot['State'] +
                    "," + snapshot['StartTime'].isoformat() +
                    "," + snapshot['VolumeId'] +
                    "," + str(snapshot['VolumeSize']) +
                    "," + snapshot['ImageId'] +
                    "," + snapshot['ImageStatus'] +
                    "," + tags_dict['SnapshotRetentionPeriod'] +
                    "," + tags_dict['CostControl'] +
                    "," + tags_dict['SnapshotSet'] +
                    "," + tags_dict['POC'])
            tags_dict.clear()

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
    
def get_ami_status(ec2, snapshot_resp):
    for snapshot in snapshot_resp['Snapshots']:
        m = re.search('Created by CreateImage.* for (ami-\S*) from', snapshot['Description'])
        if m == None:
            snapshot['ImageId'] = ''
            snapshot['ImageStatus'] = ''
        else:
            ami_id = m.group(1)
            snapshot['ImageId'] = ami_id
            try:
                resp = ec2.describe_images(ImageIds=[ami_id])
            except:
                snapshot['ImageStatus'] = 'does not exist'
            else:
                if resp['Images']:
                    snapshot['ImageStatus'] = resp['Images'][0]['State']
                else:
                    snapshot['ImageStatus'] = 'does not exist'
    return snapshot_resp

def lambda_handler(event, context):
    """Lambda function handler to create BSP Snapshot Report"""
    del context, event # Unused
    try:
        snapshots = {}
        # Get Mgmt Account Snapshots
        ec2 = boto3.client('ec2')
        resp = ec2.describe_snapshots(OwnerIds=[MGMT_ACCOUNT_ID])
        snapshots[MGMT_ACCOUNT_ALIAS] = resp['Snapshots']
    except ClientError as err:
        print("**ERROR** Querying Mgmt account snapshots: " + err.response['Error']['Message'])
    else:
        print("Mgmt account snapshots queried")
        
    try:
        # Get Tenant Account Snapshots
        sts = boto3.client('sts')
        for name, account in TENANTS.items():
            ec2 = get_tenant_ec2_client(sts, name, account)
            resp = ec2.describe_snapshots(OwnerIds=[account])
            resp = get_ami_status(ec2,resp)
            snapshots[name] = resp['Snapshots']
    except ClientError as err:
        print("**ERROR** Querying tenant " + name + " account snapshots: " + err.response['Error']['Message'])
    else:
        print("Tenant Account snapshots queried")
    
    try:
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
        print("**ERROR** Saving report to S3 bucket (" + BUCKET + "/" + REPORT_NAME + "): " + err.response['Error']['Message'])
    else:
        print("Report Saved: " + BUCKET + "/" + REPORT_NAME)

if __name__ == "__main__":
    print('Here')
    JSON_CONTENT = json.loads(open('event.json', 'r').read())
    lambda_handler(JSON_CONTENT, None)
