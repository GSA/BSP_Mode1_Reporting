variable "mgmt_account_alias" {}

variable "tenant_accounts" {}

variable "tenant_names" {}

resource "aws_iam_role" "iam_for_ami_lambda" {
  name = "iam_for_ami_lambda"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "policy_for_ami_lambda" {
  name        = "policy_for_ami_lambda"
  description = "Policy to allow creating AMI report"

  policy = <<EOF
{
  "Version": "2012-10-17",
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
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_ami_report" {
  role       = "${aws_iam_role.iam_for_ami_lambda.name}"
  policy_arn = "${aws_iam_policy.policy_for_ami_lambda.arn}"
}

resource "aws_lambda_function" "ami_report" {
  filename         = "ami_report.zip"
  function_name    = "ami_report"
  role             = "${aws_iam_role.iam_for_ami_lambda.arn}"
  handler          = "ami_report.lambda_handler"
  source_code_hash = "${base64sha256(file("ami_report.py"))}"
  runtime          = "python3.6"

  environment {
    variables = {
      ami_report_s3_bucket = "${aws_s3_bucket.ami_report.bucket}"
      mgmt_account_alias   = "${var.mgmt_account_alias}"
      tenant_accounts      = "${var.tenant_accounts}"
      tenant_names         = "${var.tenant_names}"
    }
  }
}

resource "aws_s3_bucket" "ami_report" {
  bucket        = "ami_report"
  acl           = "private"
  force_destroy = true

  tags {
    Name        = "AMI Report"
    Environment = "Dev"
  }
}