#!/usr/bin/env bash
set -euo pipefail

# 必須環境変数チェック
: "${S3_BUCKET_NAME:?'S3_BUCKET_NAME is required'}"
: "${CLOUDFRONT_DISTRIBUTION_ID:?'CLOUDFRONT_DISTRIBUTION_ID is required'}"

DEPLOY_DIR="${1:-frontend/out}"

# S3 に同期（--delete で不要ファイルを削除）
echo "Deploying to s3://${S3_BUCKET_NAME} ..."
aws s3 sync "${DEPLOY_DIR}" "s3://${S3_BUCKET_NAME}" --delete

# CloudFront キャッシュ無効化
echo "Invalidating CloudFront cache ..."
aws cloudfront create-invalidation \
  --distribution-id "${CLOUDFRONT_DISTRIBUTION_ID}" \
  --paths "/*"

echo "Deploy complete."
