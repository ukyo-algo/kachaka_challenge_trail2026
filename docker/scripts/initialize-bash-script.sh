#!/bin/bash

# Source the ROS environment.
echo "Sourcing the ROS environment from '/opt/ros/jazzy/setup.bash'."
source /opt/ros/jazzy/setup.bash

# Source the ros2_ws workspace.
echo "Sourcing the Catkin workspace from '/app/ros2_ws/install/setup.bash'."
source /app/ros2_ws/install/setup.bash

# Set bash theme
source /app/docker/scripts/bash-theme-snippet.sh

# Source the Python virtual environment.
source /app/.venv/bin/activate