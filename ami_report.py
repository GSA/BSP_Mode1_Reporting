import os
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    region = os.environ['ami_report_region']
    bucket = os.environ['ami_report_s3_bucket']
    tenant_accounts = os.environ['tenant_accounts'].split(',')
    tenant_names = os.environ['tenant_names'].split(',')
    tenants = {k:v for k, v in zip(tenant_names, tenant_accounts)}
    report_name = 'ami_report.csv'

    try:
        ec2 = boto3.resource('ec2')
        s3 = boto3.resource('s3')
        sts = boto3.client('sts')
        resp = ec2.meta.client.describe_images(Owners=['self'])
        images = resp['Images']
        csv = 'Tenant,Name,ImageId,State,CreationDate,RootDeviceType,RootDeviceName,SnapshotId'
        for image in images:
            csv = csv + "\r\nidi_sandbox," + image['Name'] + ","  + image['ImageId'] + "," + image['State'] + "," + image['CreationDate'] + "," + image['RootDeviceType'] + "," + image['RootDeviceName']
            csv = csv + "," + image['BlockDeviceMappings'][0]['Ebs']['SnapshotId']
        for name, account in tenants.items():
            role_arn = "arn:aws:iam::" + account + ":role/AMI_Reporting"
            role_session = name + "_session"
            resp = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName=role_session
            )
            ec2 = boto3.resource(
                'ec2',
                aws_access_key_id=resp['Credentials']['AccessKeyId'],
                aws_secret_access_key=resp['Credentials']['SecretAccessKey'],
                aws_session_token=resp['Credentials']['SessionToken']
            )
            resp = ec2.meta.client.describe_images(Owners=[account])
            images = resp['Images']
            for image in images:
                csv = csv + "\r\n" + name + "," + image['Name'] + ","  + image['ImageId'] + "," + image['State'] + "," + image['CreationDate'] + "," + image['RootDeviceType'] + "," + image['RootDeviceName']
                csv = csv + "," + image['BlockDeviceMappings'][0]['Ebs']['SnapshotId']

        s3.Bucket(bucket).put_object(Key=report_name, Body=csv)
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Report Saved: " + bucket + "/" + report_name)

if __name__ == "__main__":
    json_content = json.loads(open('event.json', 'r').read())
    lambda_handler(json_content, None)
