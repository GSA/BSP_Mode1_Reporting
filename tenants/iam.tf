variable "mgmt_account" {}

variable "tenant_aws_profile" {}

provider "aws" {
  profile = "${var.tenant_aws_profile}"
  alias   = "subaccount"
}

resource "aws_iam_role" "for_crossaccount_ami_reporting" {
  name     = "AMI_Reporting"
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

resource "aws_iam_policy" "for_crossaccount_ami_reporting" {
  name        = "policy_for_crossaccount_ami_reporting"
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

resource "aws_iam_role_policy_attachment" "test-ami-attach" {
  role       = "${aws_iam_role.for_crossaccount_ami_reporting.name}"
  policy_arn = "${aws_iam_policy.for_crossaccount_ami_reporting.arn}"
  provider   = "aws.subaccount"
}
