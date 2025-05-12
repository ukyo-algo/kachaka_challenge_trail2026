#!/bin/bash

set -eu

# Build the Docker image with the Nvidia GL library.
echo "starting build"
docker build -t weblab/v1-kachaka-jazzy -f ./docker/Dockerfile .
echo "finished build"
