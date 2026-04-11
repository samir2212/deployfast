#!/bin/bash
# ─────────────────────────────────────────────
# deploy.sh
# Builds the frontend and deploys to S3 + CloudFront
# Run from the tutaia-web directory
# ─────────────────────────────────────────────
set -e

AWS_REGION="eu-central-1"
BUCKET="tutaia-frontend-856930835134"
DISTRIBUTION_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Comment=='Tutaia Frontend - deployfast.tutaia.com'].Id" \
  --output text 2>/dev/null)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🚀 Deploying Tutaia Frontend"
echo "   Bucket: ${BUCKET}"
echo "   Domain: deployfast.tutaia.com"
echo ""

# ── Step 1: Build ────────────────────────────
echo "🔨 Building frontend..."
cd "${WEB_DIR}"
npm run build

# ── Step 2: Sync to S3 ──────────────────────
echo "⬆️  Uploading to S3..."
aws s3 sync dist/ "s3://${BUCKET}" \
  --delete \
  --region "${AWS_REGION}" \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html" \
  --exclude "*.json"

# Upload index.html and JSON with short cache
aws s3 cp dist/index.html "s3://${BUCKET}/index.html" \
  --region "${AWS_REGION}" \
  --cache-control "public, max-age=0, must-revalidate" \
  --content-type "text/html"

# Upload any JSON files (like manifest) with short cache
find dist -name "*.json" -exec sh -c '
  for f do
    key="${f#dist/}"
    aws s3 cp "$f" "s3://'"${BUCKET}"'/${key}" \
      --region "'"${AWS_REGION}"'" \
      --cache-control "public, max-age=0, must-revalidate"
  done
' sh {} +

# ── Step 3: Invalidate CloudFront ────────────
if [ -n "${DISTRIBUTION_ID}" ]; then
  echo "🔄 Invalidating CloudFront cache..."
  aws cloudfront create-invalidation \
    --distribution-id "${DISTRIBUTION_ID}" \
    --paths "/*" \
    --query "Invalidation.Id" \
    --output text
else
  echo "⚠️  CloudFront distribution not found, skipping invalidation"
fi

echo ""
echo "✅ Frontend deployed!"
echo "   URL: https://deployfast.tutaia.com"
