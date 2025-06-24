FROM ros:jazzy

WORKDIR /app/

# Setup dependencies
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    git \
    curl \
    make \
    terminator \
    sudo \
    xauth \
    '~nros-jazzy-rqt*' \
    ros-jazzy-teleop-twist-keyboard \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

COPY ./ros2_ws/ /app/ros2_ws/
WORKDIR /app/ros2_ws/
# Install rosdep dependencies 
RUN apt update && \
    rosdep update && \
    rosdep install -i -r -y --from-paths src

# Install X11 requirements
RUN apt-get update -q && apt-get install -y \
    iputils-ping telnet x11-apps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./docker/scripts/ /app/docker/scripts/
RUN chmod +x /app/docker/scripts/*.sh

# Setup uv
WORKDIR /app/ 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_LINK_MODE=copy

# Create a non-root user that matches the host user
ARG USER_ID
ARG GROUP_ID
ARG USERNAME=trail

# Create group first, handle existing group
RUN getent group ${GROUP_ID} >/dev/null 2>&1 || groupadd -g ${GROUP_ID} ${USERNAME}

# Create user, handle existing user
RUN if ! getent passwd ${USER_ID} >/dev/null 2>&1; then \
        useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash ${USERNAME}; \
    else \
        existing_user=$(getent passwd ${USER_ID} | cut -d: -f1); \
        usermod -l ${USERNAME} -d /home/${USERNAME} -m $existing_user 2>/dev/null || true; \
    fi

# Add user to sudoers
RUN echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up directories with proper permissions (minimal chown)
RUN mkdir -p /home/${USERNAME}/.local/share && \
    chown -R ${USER_ID}:${GROUP_ID} /home/${USERNAME} && \
    chown ${USER_ID}:${GROUP_ID} /app && \
    chmod +x /app/docker/scripts/*.sh

# Switch to non-root user
USER ${USERNAME}

# Setup user-specific configurations
RUN echo 'source /app/docker/scripts/initialize-bash-script.sh' >> ~/.bashrc && \
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc

# Setup uv for the user
COPY --chown=${USER_ID}:${GROUP_ID} ./pyproject.toml uv.lock .python-version /app/

RUN uv python install 3.12 && \
    uv python pin 3.12 && \
    uv venv

# Overwrite the entry point of the parent image
ENTRYPOINT []

# Enter the container with a Bash shell
CMD ["/bin/bash"]
