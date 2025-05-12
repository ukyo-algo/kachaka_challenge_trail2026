FROM ros:jazzy

WORKDIR /app/

# Setup dependencies
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    git \
    curl \
    make \
    terminator \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

COPY ./ros2_ws/ /app/ros2_ws/
WORKDIR /app/ros2_ws/
# Install rosdep dependencies 
RUN sudo apt update && \
    rosdep update && \
    rosdep install -i -r -y --from-paths src

# Install X11 requirements
RUN apt-get update -q && apt-get install -y \
    iputils-ping telnet x11-apps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./docker/scripts/ /app/docker/scripts/
RUN chmod +x /app/docker/scripts/*.sh
RUN echo 'source /app/docker/scripts/initialize-bash-script.sh' >> ~/.bashrc

# Setup uv
WORKDIR /app/ 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_LINK_MODE=copy
RUN echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc && \
    uv python install 3.12 && \
    uv python pin 3.12 && \
    uv venv

# Overwrite the entry point of the parent image
ENTRYPOINT []

# Enter the container with a Bash shell
CMD ["/bin/bash"]
