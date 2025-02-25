#!/bin/bash
set -e

REPO="$(pwd)"
REF="$(git describe --tags --always)"
LAMBDA_ZIP="$REPO/nekobus-$REF.zip"
TMP_DIR="$REPO/.tmp_lambda"

# reset tmp dir
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

# run container to collect all lambda assets
docker run --rm \
       -v "$REPO:/var/lambda_mount" \
       "python:3.12" \
       bash -c 'mkdir /tmp/.tmp_lambda && pip install --root-user-action=ignore -U pip wheel -q && pip install --root-user-action=ignore --platform manylinux2014_x86_64 --target=package --implementation cp --python-version 3.12 --only-binary=:all: --upgrade /var/lambda_mount/ -q -t /tmp/.tmp_lambda && mv /tmp/.tmp_lambda /var/lambda_mount/'

# cleanup
rm -rf build
rm -rf nekobus.egg-info

# zip lambda assets
cd "$TMP_DIR"
rm -rf bin
rm -rf build
#rm -r bin build
zip -r9 "$LAMBDA_ZIP" . > /dev/null
rm -rf "$TMP_DIR"

# add lambda function to lambda ZIP archive
cd "$REPO/lambda"
zip -g "$LAMBDA_ZIP" lambda_function.py > /dev/null

# this is the end
echo $(basename "$LAMBDA_ZIP")
