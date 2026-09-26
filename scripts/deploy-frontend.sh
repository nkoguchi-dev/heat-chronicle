#!/usr/bin/env bash
set -euo pipefail

# 必須環境変数チェック
: "${S3_BUCKET_NAME:?'S3_BUCKET_NAME is required'}"
: "${CLOUDFRONT_DISTRIBUTION_ID:?'CLOUDFRONT_DISTRIBUTION_ID is required'}"

DEPLOY_DIR="${1:-frontend/dist}"

# --delete を空・誤指定のディレクトリに対して実行しない。
if [[ ! -f "${DEPLOY_DIR}/index.html" || ! -d "${DEPLOY_DIR}/assets" ]] \
  || [[ -z "$(find "${DEPLOY_DIR}/assets" -type f -print -quit)" ]]; then
  echo "Vite artifact is missing index.html or asset files: ${DEPLOY_DIR}" >&2
  exit 1
fi

# HTML 等と hashed assets を別々に同期し、それぞれの cache policy を指定する。
# --delete は既存の公開ファイルと assets/ の範囲に限る。
echo "Deploying to s3://${S3_BUCKET_NAME} ..."
aws s3 sync "${DEPLOY_DIR}" "s3://${S3_BUCKET_NAME}" \
  --delete --exclude 'assets/*' --cache-control 'public,max-age=300'
aws s3 sync "${DEPLOY_DIR}/assets" "s3://${S3_BUCKET_NAME}/assets" \
  --delete --cache-control 'public,max-age=31536000,immutable'

# CloudFront キャッシュ無効化
echo "Invalidating CloudFront cache ..."
aws cloudfront create-invalidation \
  --distribution-id "${CLOUDFRONT_DISTRIBUTION_ID}" \
  --paths "/*"

echo "Deploy complete."
