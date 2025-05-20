#!/bin/bash

echo 'alias create_ros2_pkg="cookiecutter ../../template/"' >> ~/.bashrc

if [ ! -d "/app/.venv" ]; then
    echo "Creating virtual environment..."
    cd /app
    uv venv
    uv sync
fi

# Keep the Docker container running in the background.
# https://stackoverflow.com/questions/30209776/docker-container-will-automatically-stop-after-docker-run-d
tail -f /dev/null
