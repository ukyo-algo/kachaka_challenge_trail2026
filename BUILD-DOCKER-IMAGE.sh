#!/bin/bash

set -eu

# Build the Docker image with the Nvidia GL library.
echo "starting build"
docker build -t weblab/v1-kachaka-jazzy --build-arg USER_ID="$(id -u)" --build-arg GROUP_ID="$(id -g)" -f ./docker/Dockerfile .

pushd external/kachaka-api
docker buildx build -t kachaka-api --target kachaka-grpc-ros2-bridge -f Dockerfile.ros2 . --build-arg BASE_ARCH=x86_64 --load
popd

echo "finished build"
