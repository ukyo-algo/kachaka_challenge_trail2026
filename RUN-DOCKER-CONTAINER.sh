#!/bin/bash

# Script to run a Docker container for HSR development
# Usage: ./RUN-DOCKER-CONTAINER.sh [PROJECT_NAME] [HSR_NUMBER]

set -e

# Change to the directory containing the script
cd "$(dirname "$0")"

function setup_project_name() {
  if [ -n "$KACHAKA_PROJECT_NAME" ]; then
    PROJECT="$KACHAKA_PROJECT_NAME"
    HSR_NUMBER="$1"
  elif [ -n "$1" ]; then
    PROJECT="$1"
    HSR_NUMBER="$2"
  else
    echo "Set KACHAKA_PROJECT_NAME (e.g. 'export KACHAKA_PROJECT_NAME=mytest')"
    exit 1
  fi

  export KACHAKA_PROJECT_NAME="$PROJECT"
  CONTAINER="${PROJECT}_kachaka_project_1"
  echo "$0: PROJECT=${PROJECT}"
  echo "$0: CONTAINER=${CONTAINER}"
}

function run_docker_container() {
  # Check if container already exists
  if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER}$" || [ $? -eq 1 ]; then
    # Container exists if grep returned 0, doesn't exist if grep returned 1
    if [ "$(docker ps -a --format '{{.Names}}' | grep -E "^${CONTAINER}$" || true)" ]; then
      echo "Container '${CONTAINER}' already exists."
      echo "Starting the existing container..."
      docker start "${CONTAINER}" || {
        echo "Failed to start container. Removing and recreating..."
        docker rm "${CONTAINER}" || true
        docker compose --compatibility -p "${PROJECT}" -f ./docker/docker-compose.yml up -d
      }
    else
      echo "Container '${CONTAINER}' does not exist."
      echo "Creating a new container..."
      docker compose --compatibility -p "${PROJECT}" -f ./docker/docker-compose.yml up -d
    fi
  fi
}

function setup_x11_auth() {
  if [ -n "$DISPLAY" ]; then
    XAUTH_RESULT="$(xauth list "$DISPLAY" 2>/dev/null || true)"
    echo "XAUTH_RESULT: $XAUTH_RESULT"
    if [ -z "$XAUTH_RESULT" ]; then
      xauth generate "$DISPLAY" . 2>/dev/null || true
    fi

    if XAUTH_LIST=$(xauth list "$DISPLAY" 2>/dev/null || true) && [ -n "$XAUTH_LIST" ]; then
      read -r _ XAUTH_PROTOCOL XAUTH_KEY <<<"$XAUTH_LIST"
      docker exec -it "$CONTAINER" bash -c "touch /root/.Xauthority; xauth add $DISPLAY $XAUTH_PROTOCOL $XAUTH_KEY" || true
    else
      echo "Warning: Could not set up X11 authentication. GUI applications may not work."
    fi
  fi
}

function enter_container() {
    docker exec -it "$CONTAINER" bash || {
        echo "Failed to enter the container. Please check if the container is running."
        exit 1
    }
}

echo "Starting Docker container for HSR development..."
setup_project_name "$@"

echo "Running Docker container..."
run_docker_container

echo "Setting up X11 authentication..."
setup_x11_auth

echo "Entering the container..."
enter_container
