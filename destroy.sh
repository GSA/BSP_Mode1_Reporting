MASTER=$(grep mgmt_account_alias terraform.tfvars | sed s/^.*\=[[:space:]]*// | sed s/\"//g)

echo "Master: $MASTER"
export AWS_PROFILE=$MASTER

OIFS=$IFS
IFS=','
SUBS=$(grep tenant_names terraform.tfvars | sed s/^.*\=[[:space:]]*// | sed s/\"//g)

terraform workspace select default
terraform destroy -force

cd tenants

for S in $SUBS
do
  echo "Subaccount: $S"
  export TF_VAR_tenant_aws_profile=$S
  terraform workspace select $S
  terraform destroy -force
done

cd ..
terraform workspace select default

export IFS=$OIFS
