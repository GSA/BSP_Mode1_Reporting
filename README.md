# ami-report #

AMI report using Lambda functions and Amazon SES

![Diagram](diagram.png)

There are two Lambda functions.  One does a DescribeImages query for each tenant
account, formats the data into CSV and saves the CSV to an S3 bucket.  The
second Lambda function creates a multi-part MIME Email, and attaches the report
from the S3 bucket and sends it via Amazon Simple Email Service (SES) to a list
of recipients.

## IAM Roles and Policies ##

### Tenant Account Role ###

Cross-account permissions are required for the Lambda function in the
"management" account to query the "tenant" accounts.  This is done by creating
an IAM role with delegation to the management account.  See the [Terraform
configuration](tenants/iam.tf#L3) for details.

### Tenant Account Policy ###

Attached to the tenant IAM role is a single policy with `ec2:DescribeImages`
action allowed.

```
"Statement": [
  {
    "Action": [
      "ec2:DescribeImages"
    ],
    "Effect": "Allow",
    "Resource": "*"
  }
]
```

### AMI Report Lambda Function IAM Policy ###

The Lambda function which creates the AMI Report is assinged an IAM role in the
management account with a single policy attached that allows it do perform all of
its necessary functions.

```json
"Statement": [
  {
    "Action": [
      "ec2:DescribeImages",
      "s3:PutObject",
      "sts:AssumeRole",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ],
    "Effect": "Allow",
    "Resource": "*"
  }
]
```

####  ec2:DescribeImages ####

Allows the Lambda function to query the Images in the management account.

#### s3:PutObject ####

Allows the Lambda function to write the CSV report to an S3 bucket

#### sts:AssumeRole ####

Allows the Lambda function to assume the delegated tenant IAM role and query
`DescribeImages` in the tenant accounts.

#### logs:CreateLogGroup, etc. ####

`logs:CreateLogGroup`, `logs:CreateLogStream` and `logs:PutLogEvents` actions
are required by all Lambda functions to log their actions.

### Report Emailing Lambda Function IAM Policy ###

The Lambda function which Emails the AMI Report is assinged an IAM role in the
management account with a single policy attached that allows it do perform all of
its necessary functions.

```json
"Statement": [
  {
    "Action": [
      "ses:SendRawEmail",
      "s3:GetObject",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ],
    "Effect": "Allow",
    "Resource": "*"
  }
]
```

#### ses:SendRawEmail ####

Allows Lambda function to send Email via Amazon SES.

#### s3:GetObject ####

Allows Lambda function to read the report from an Amazon S3 bucket.

#### logs:CreateLogGroup, etc. ####

`logs:CreateLogGroup`, `logs:CreateLogStream` and `logs:PutLogEvents` actions
are required by all Lambda functions to log their actions.

## TODO ##

- Add tests for CircleCI/fix configuration
    - Add pylint to CircleCI tests
    - Fix pylint issues
    - Add [TFLint](https://github.com/wata727/tflint) to CircleCI tests
- Fix TFLint issues
- Use DateTime stamp for report file name
- Schedule lambda to generate reports every night
- Handle AMIs with multiple snapshots
- Parameterize
