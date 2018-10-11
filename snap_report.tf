variable "mgmt_account" {}

variable "mgmt_account_alias" {}

variable "tenant_accounts" {}

variable "tenant_names" {}

variable "schedule_expression" {}

resource "aws_iam_role" "iam_for_snapshot_lambda" {
  name = "iam_for_snapshot_lambda"

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

resource "aws_iam_policy" "policy_for_snapshot_lambda" {
  name        = "policy_for_snapshot_lambda"
  description = "Policy to allow creating Snapshot report"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "ec2:DescribeSnapshots",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Effect": "Allow",
      "Resource": "*"
    },
    {
      "Action": [
        "sts:AssumeRole"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:iam::*:role/Snapshot_Reporting"
    },
    {
      "Action": [
        "s3:PutObject"
      ],
      "Effect": "Allow",
      "Resource": "${aws_s3_bucket.snapshot_report.arn}/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Encrypt"
      ],
      "Resource": "${aws_kms_key.snapshot_report_key.arn}"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_snapshot_report" {
  role       = "${aws_iam_role.iam_for_snapshot_lambda.name}"
  policy_arn = "${aws_iam_policy.policy_for_snapshot_lambda.arn}"
}

resource "aws_lambda_function" "snapshot_report" {
  filename         = "snapshot_report.zip"
  function_name    = "snapshot_report"
  role             = "${aws_iam_role.iam_for_snapshot_lambda.arn}"
  handler          = "snapshot_report.lambda_handler"
  source_code_hash = "${base64sha256(file("snapshot_report.py"))}"
  runtime          = "python3.6"
  timeout          = 6

  environment {
    variables = {
      snapshot_report_s3_bucket = "${aws_s3_bucket.snapshot_report.bucket}"
      mgmt_account_alias        = "${var.mgmt_account_alias}"
      tenant_accounts           = "${var.tenant_accounts}"
      tenant_names              = "${var.tenant_names}"
      snapshot_report_key_id    = "${aws_kms_key.snapshot_report_key.key_id}"
    }
  }
}

resource "aws_cloudwatch_event_rule" "snapshot_report_event_rule" {
  name                = "snapshot_report_event_rule"
  description         = "Triggers snapshot_report Lambda function according to schedule expression"
  schedule_expression = "${var.schedule_expression}"
}

resource "aws_cloudwatch_event_target" "snapshot_report_event_target" {
  rule      = "${aws_cloudwatch_event_rule.snapshot_report_event_rule.name}"
  target_id = "snapshot_report"
  arn       = "${aws_lambda_function.snapshot_report.arn}"
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_snapshot_report" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.snapshot_report.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.snapshot_report_event_rule.arn}"
}

resource "aws_kms_key" "snapshot_report_key" {
  description             = "Key for BSP Mode1 Snapshot Report S3 bucket"
  deletion_window_in_days = 7

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${var.mgmt_account}:root"
      },
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "Allow use of the key",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "${aws_iam_role.iam_for_snapshot_lambda.arn}",
          "${aws_iam_role.iam_for_ses_lambda.arn}"
        ]
      },
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

resource "aws_kms_alias" "snapshot_report_key" {
  name          = "alias/snapshot_report_key"
  target_key_id = "${aws_kms_key.snapshot_report_key.key_id}"
}

resource "aws_s3_bucket" "snapshot_report" {
  bucket        = "snapshot_report"
  acl           = "private"
  force_destroy = true

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = "${aws_kms_key.snapshot_report_key.arn}"
        sse_algorithm     = "aws:kms"
      }
    }
  }

  lifecycle_rule {
    id      = "delete"
    enabled = true

    expiration {
      days = 7
    }
  }

  tags {
    Name = "Snapshot Report"
  }
}
