variable "mgmt_account" {}

variable "tenant_aws_profile" {}

provider "aws" {
  profile = "${var.tenant_aws_profile}"
  alias   = "subaccount"
}

resource "aws_iam_role" "ami_reporting_iam_role" {
  name     = "ami-reporting"
  provider = "aws.subaccount"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "AWS": "arn:aws:iam::${var.mgmt_account}:root"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "ami_reporting_iam_policy" {
  name        = "ami-reporting"
  description = "Policy to allow cross-account AMI reporting"
  provider    = "aws.subaccount"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "ec2:DescribeImages"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "ami_reporting_iam_role_policy_attachment" {
  role       = "${aws_iam_role.ami_reporting_iam_role.name}"
  policy_arn = "${aws_iam_policy.ami_reporting_iam_policy.arn}"
  provider   = "aws.subaccount"
}

resource "aws_iam_role" "snapshot_reporting_iam_role" {
  name     = "snapshot-reporting"
  provider = "aws.subaccount"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "AWS": "arn:aws:iam::${var.mgmt_account}:root"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "snapshot_reporting_iam_policy" {
  name        = "snapshot-reporting"
  description = "Policy to allow cross-account snapshot reporting"
  provider    = "aws.subaccount"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "ec2:DescribeSnapshots",
		"ec2:DescribeImages"
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "snapshot_reporting_iam_role_policy_attachment" {
  role       = "${aws_iam_role.snapshot_reporting_iam_role.name}"
  policy_arn = "${aws_iam_policy.snapshot_reporting_iam_policy.arn}"
  provider   = "aws.subaccount"
}