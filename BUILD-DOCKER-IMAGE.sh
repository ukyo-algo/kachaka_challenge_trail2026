#!/bin/bash

set -eu

# Parse command line arguments
BUILD_KACHAKA_API=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --with-kachaka-api)
      BUILD_KACHAKA_API=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--with-kachaka-api]"
      echo "  --with-kachaka-api    Include kachaka-api build (default: false)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Build the Docker image with the Nvidia GL library.
echo "starting build"
docker build -t weblab/v1-kachaka-jazzy --build-arg USER_ID="$(id -u)" --build-arg GROUP_ID="$(id -g)" -f ./docker/Dockerfile .

if [ "$BUILD_KACHAKA_API" = true ]; then
  echo "Building kachaka-api..."
  pushd external/kachaka-api
  docker buildx build -t kachaka-api --target kachaka-grpc-ros2-bridge -f Dockerfile.ros2 . --build-arg BASE_ARCH=x86_64 --load
  popd
else
  echo "Skipping kachaka-api build (use --with-kachaka-api to include it)"
fi

echo "finished build"
