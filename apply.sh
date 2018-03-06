MASTER=$(grep mgmt_account_alias terraform.tfvars | sed s/^.*\=[[:space:]]*// | sed s/\"//g)

echo "Master: $MASTER"
export AWS_PROFILE=$MASTER

OIFS=$IFS
IFS=','
SUBS=$(grep tenant_names terraform.tfvars | sed s/^.*\=[[:space:]]*// | sed s/\"//g)

terraform workspace select default
rm *.zip
zip ami_report.zip ami_report.py
zip mail_report.zip mail_report.py
terraform apply --auto-approve

cd tenants

for S in $SUBS
do
  echo "Subaccount: $S"
  export TF_VAR_tenant_aws_profile=$S
  terraform workspace new $S
  terraform workspace select $S
  terraform apply --auto-approve
done

cd ..
terraform workspace select default

export IFS=$OIFS
