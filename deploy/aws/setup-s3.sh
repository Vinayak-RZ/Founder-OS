#!/usr/bin/env bash
# Create S3 vault bucket + IAM instance profile for Founder OS EC2.
# Requires: AWS CLI configured (aws sts get-caller-identity must succeed).
#
# Usage:
#   ./deploy/aws/setup-s3.sh BUCKET_NAME REGION INSTANCE_ID [EC2_HOST] [SSH_KEY]
#
# Example:
#   ./deploy/aws/setup-s3.sh founder-os-vault-nawab-os ap-southeast-2 i-0e529afebb6c2f59c 15.135.253.12 nawab.pem
set -euo pipefail

BUCKET="${1:?bucket name required}"
REGION="${2:?region required}"
INSTANCE_ID="${3:?instance id required}"
EC2_HOST="${4:-}"
SSH_KEY="${5:-}"

ROLE_NAME="FounderOSVaultRole"
PROFILE_NAME="FounderOSVaultProfile"
POLICY_NAME="FounderOSVaultS3Policy"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> AWS identity"
aws sts get-caller-identity

echo "==> S3 bucket: s3://${BUCKET} (${REGION})"
if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "    Bucket already exists"
else
  if [[ "$REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"
  else
    aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=${REGION}"
  fi
  aws s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
fi

echo "==> IAM role: ${ROLE_NAME}"
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://${SCRIPT_DIR}/iam-trust-ec2.json"
fi

POLICY_DOC="$(sed "s/BUCKET_NAME/${BUCKET}/g" "${SCRIPT_DIR}/iam-s3-policy.json")"
aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name "$POLICY_NAME" \
  --policy-document "$POLICY_DOC"

echo "==> Instance profile: ${PROFILE_NAME}"
if ! aws iam get-instance-profile --instance-profile-name "$PROFILE_NAME" >/dev/null 2>&1; then
  aws iam create-instance-profile --instance-profile-name "$PROFILE_NAME"
  aws iam add-role-to-instance-profile \
    --instance-profile-name "$PROFILE_NAME" --role-name "$ROLE_NAME"
else
  aws iam add-role-to-instance-profile \
    --instance-profile-name "$PROFILE_NAME" --role-name "$ROLE_NAME" 2>/dev/null || true
fi

echo "==> Attach profile to ${INSTANCE_ID}"
EXISTING="$(aws ec2 describe-iam-instance-profile-associations \
  --filters "Name=instance-id,Values=${INSTANCE_ID}" \
  --query 'IamInstanceProfileAssociations[0].AssociationId' --output text 2>/dev/null || true)"
if [[ -n "$EXISTING" && "$EXISTING" != "None" ]]; then
  aws ec2 disassociate-iam-instance-profile --association-id "$EXISTING"
  sleep 5
fi
aws ec2 associate-iam-instance-profile \
  --instance-id "$INSTANCE_ID" \
  --iam-instance-profile "Name=${PROFILE_NAME}"

if [[ -n "$EC2_HOST" && -n "$SSH_KEY" ]]; then
  echo "==> Update /etc/founder-os/env on ${EC2_HOST}"
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "ubuntu@${EC2_HOST}" bash -s <<EOF
set -euo pipefail
sudo sed -i '/^AWS_S3_BUCKET=/d;/^AWS_REGION=/d;/^AWS_ACCESS_KEY_ID=/d;/^AWS_SECRET_ACCESS_KEY=/d' /etc/founder-os/env
sudo sed -i 's/\r\$//' /etc/founder-os/env
printf '%s\n' 'AWS_S3_BUCKET=${BUCKET}' 'AWS_REGION=${REGION}' | sudo tee -a /etc/founder-os/env >/dev/null
sudo systemctl restart founder-os
sleep 3
curl -sf http://127.0.0.1:8787/api/health
EOF
fi

echo ""
echo "S3 vault ready."
echo "  Bucket:  s3://${BUCKET}"
echo "  Region:  ${REGION}"
echo "  Profile: ${PROFILE_NAME} -> ${INSTANCE_ID}"
echo "Verify: curl https://nawab-os.stamped.work/api/health  # expect storage:s3"
