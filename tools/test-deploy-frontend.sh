#!/usr/bin/env bash
set -euo pipefail

test_dir="$(mktemp -d)"
trap 'rm -rf -- "${test_dir}"' EXIT
mkdir -p "${test_dir}/dist/assets"
printf '<html></html>\n' >"${test_dir}/dist/index.html"
printf 'asset\n' >"${test_dir}/dist/assets/app-hash.js"

export AWS_CALLS_LOG="${test_dir}/aws-calls.log"
export S3_BUCKET_NAME='test-frontend-bucket'
export CLOUDFRONT_DISTRIBUTION_ID='TESTDISTRIBUTION'

aws() {
  printf '%s\n' "$*" >>"${AWS_CALLS_LOG}"
  if [[ "${AWS_FAIL_ASSETS:-}" == 1 && "$*" == *'s3://test-frontend-bucket/assets'* ]]; then
    return 1
  fi
}
export -f aws

bash scripts/deploy-frontend.sh "${test_dir}/dist"
printf '%s\n' \
  "s3 sync ${test_dir}/dist s3://test-frontend-bucket --delete --exclude assets/* --cache-control public,max-age=300" \
  "s3 sync ${test_dir}/dist/assets s3://test-frontend-bucket/assets --delete --cache-control public,max-age=31536000,immutable" \
  'cloudfront create-invalidation --distribution-id TESTDISTRIBUTION --paths /*' \
  | diff -u - "${AWS_CALLS_LOG}"

: >"${AWS_CALLS_LOG}"
if bash scripts/deploy-frontend.sh "${test_dir}/missing"; then
  echo 'Missing Vite artifact must fail before S3 sync' >&2
  exit 1
fi
[[ ! -s "${AWS_CALLS_LOG}" ]]

: >"${AWS_CALLS_LOG}"
rm "${test_dir}/dist/assets/app-hash.js"
if bash scripts/deploy-frontend.sh "${test_dir}/dist"; then
  echo 'Empty Vite assets directory must fail before S3 sync' >&2
  exit 1
fi
[[ ! -s "${AWS_CALLS_LOG}" ]]
printf 'asset\n' >"${test_dir}/dist/assets/app-hash.js"

: >"${AWS_CALLS_LOG}"
export AWS_FAIL_ASSETS=1
if bash scripts/deploy-frontend.sh "${test_dir}/dist"; then
  echo 'Failed asset sync must stop before CloudFront invalidation' >&2
  exit 1
fi
[[ "$(wc -l <"${AWS_CALLS_LOG}")" -eq 2 ]]

echo 'Frontend deployment command tests passed.'
