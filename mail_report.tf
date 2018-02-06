variable "sender" {}

variable "recipients" {}

resource "aws_iam_role" "iam_for_ses_lambda" {
  name = "iam_for_ses_lambda"

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

resource "aws_iam_policy" "policy_for_ses_lambda" {
  name        = "policy_for_ses_lambda"
  description = "Policy to allow sending SES e-mails"

  policy = <<EOF
{
  "Version": "2012-10-17",
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
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_mail_report" {
  role       = "${aws_iam_role.iam_for_ses_lambda.name}"
  policy_arn = "${aws_iam_policy.policy_for_ses_lambda.arn}"
}

resource "aws_lambda_permission" "allow_ami_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.mail_report.arn}"
  principal     = "s3.amazonaws.com"
  source_arn    = "${aws_s3_bucket.ami_report.arn}"
}

resource "aws_lambda_function" "mail_report" {
  filename         = "mail_report.zip"
  function_name    = "mail_report"
  role             = "${aws_iam_role.iam_for_ses_lambda.arn}"
  handler          = "mail_report.lambda_handler"
  source_code_hash = "${base64sha256(file("mail_report.py"))}"
  runtime          = "python3.6"

  environment {
    variables = {
      sender     = "${var.sender}"
      recipients = "${var.recipients}"
    }
  }
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = "${aws_s3_bucket.ami_report.id}"

  lambda_function {
    lambda_function_arn = "${aws_lambda_function.mail_report.arn}"
    events              = ["s3:ObjectCreated:*"]

    # filter_prefix       = "AWSLogs/"
    filter_suffix = ".csv"
  }
}
