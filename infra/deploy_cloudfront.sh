#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${ROOT_DIR}/infra/cloudfront_config.json"

echo "Creating CloudFront distribution for PATHwise frontend..."
aws cloudfront create-distribution \
  --distribution-config "file://${CONFIG_FILE}" \
  --query "Distribution.{Id:Id,DomainName:DomainName,Status:Status}" \
  --output table
