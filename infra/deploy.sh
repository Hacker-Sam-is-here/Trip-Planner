#!/usr/bin/env bash
set -euo pipefail

# PATHwise Lambda and Infrastructure Deployment Script

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [ -f .env ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs)
fi

S3_BUCKET="${S3_BUCKET:-pathwise-assets}"
S3_MODEL_KEY="${S3_MODEL_KEY:-models/air_quality_model.pkl}"
LAMBDA_FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-pathwise-analyze-route}"
BUILD_DIR="${ROOT_DIR}/build"
PACKAGE_ZIP="${ROOT_DIR}/lambda_package.zip"

echo "=== Step 1: Uploading ML model artifact to S3 ==="
if [ -f "ml/air_quality_model.pkl" ]; then
  aws s3 cp ml/air_quality_model.pkl "s3://${S3_BUCKET}/${S3_MODEL_KEY}"
  echo "Model uploaded to s3://${S3_BUCKET}/${S3_MODEL_KEY}"
else
  echo "Error: ml/air_quality_model.pkl not found!"
  exit 1
fi

echo "=== Step 2: Packaging backend with dependencies ==="
rm -rf "${BUILD_DIR}" "${PACKAGE_ZIP}"
mkdir -p "${BUILD_DIR}"

if command -v uv &> /dev/null; then
  uv pip install --python 3.12 --target "${BUILD_DIR}" \
    pandas==2.2.3 scikit-learn==1.6.0 numpy==2.1.3 requests==2.32.3 python-dotenv==1.0.1 --quiet
else
  pip install --target "${BUILD_DIR}" \
    pandas==2.2.3 scikit-learn==1.6.0 numpy==2.1.3 requests==2.32.3 python-dotenv==1.0.1 --quiet
fi

cp -r backend "${BUILD_DIR}/"
find "${BUILD_DIR}" -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}" -name "*.pyc" -delete 2>/dev/null || true
find "${BUILD_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -rf "${BUILD_DIR}"/*.dist-info 2>/dev/null || true

python -c "import shutil; shutil.make_archive('${PACKAGE_ZIP%.zip}', 'zip', '${BUILD_DIR}')"
rm -rf "${BUILD_DIR}"
echo "Deployment package created: ${PACKAGE_ZIP}"

echo "=== Step 3: Deploying or updating Lambda function ==="
aws s3 cp "${PACKAGE_ZIP}" "s3://${S3_BUCKET}/lambda/lambda_package.zip"
if aws lambda get-function --function-name "${LAMBDA_FUNCTION_NAME}" --region "${AWS_DEFAULT_REGION:-ap-south-1}" > /dev/null 2>&1; then
  echo "Updating existing Lambda function code..."
  aws lambda update-function-code \
    --function-name "${LAMBDA_FUNCTION_NAME}" \
    --s3-bucket "${S3_BUCKET}" \
    --s3-key "lambda/lambda_package.zip" \
    --region "${AWS_DEFAULT_REGION:-ap-south-1}"
else
  echo "Lambda function ${LAMBDA_FUNCTION_NAME} does not exist yet."
fi

echo "=== Step 4: Setting up DynamoDB table ==="
python infra/dynamo_setup.py

echo "=== Step 5: Storing permanent demo scenario ==="
python -c "from backend.dynamo_cache import store_demo_scenario; store_demo_scenario()"

echo "=== Deployment complete! ==="
