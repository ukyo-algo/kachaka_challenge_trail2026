# kachaka_challenge_trail2025

## Overview

This repository provides a ROS 2-based development environment and tools for working with [Kachaka](https://kachaka.life/), including simulation, navigation, mapping, and API integration. It combines official Kachaka API resources and custom development kits for both real and simulated robots.

## Requirements

For Windows:
- WSL 2 (Follow [this instruction](https://learn.microsoft.com/en-us/windows/wsl/install) to install WSL and Ubuntu distribution)
- Docker (Follow [this instruction](https://docs.docker.com/engine/install/ubuntu/) to install)

For MacOS:
- Docker Desktop (Follow [this instruction](https://docs.docker.com/desktop/install/mac-install/) to install)

You also need to register your GitHub account and register your SSH public key to GitHub to pull the repository.

## Repository Structure

- `ros2_ws/src/kachaka_ros2_dev_kit/`  
    ROS 2 development kit for Kachaka, including:
    - `kachaka_description`: Robot description package.
    - `kachaka_interfaces`: Custom message and action definitions.
    - `kachaka_nav2_bringup`: Launch and config for Nav2 stack.
    - `kachaka_mapping`: Mapping tools.
    - `kachaka_gazebo`: Gazebo Ignition simulation environment.
    - `utils/joy_controller`: Joystick teleoperation utility.

- `external/kachaka-api/`  
    Official Kachaka API repository (as a submodule or copy), including:
    - Python and ROS 2 SDKs
    - Demos and documentation
    - Contribution and linting tools

- `docker/`  
    Scripts and snippets for containerized development environments.

## Getting Started
### Clone the Repository

Clone this repository and its submodules:

```bash
git clone --recurse-submodules git@github.com:uamea/kachaka_challenge_trail2025.git
cd kachaka_challenge_trail2025
```

### Requirements

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- NVIDIA GPU recommended for simulation
- Kachaka software v3.8.5 (for real robot integration)

### Usage

- **Simulation:**  
    See [kachaka_gazebo/README.md](ros2_ws/src/kachaka_ros2_dev_kit/kachaka_gazebo/README.md)
- **Mapping:**  
    See [docs/sim/mapping_sim.md](ros2_ws/src/kachaka_ros2_dev_kit/docs/sim/mapping_sim.md)
- **Navigation:**  
    - Real robot: [docs/navigation.md](ros2_ws/src/kachaka_ros2_dev_kit/docs/navigation.md)
    - Simulation: [docs/sim/navigation_sim.md](ros2_ws/src/kachaka_ros2_dev_kit/docs/sim/navigation_sim.md)

## Kachaka API

- Official API and SDKs are included under `external/kachaka-api/`.
- See [external/kachaka-api/README.md](external/kachaka-api/README.md) for API usage, supported features, and contribution guidelines.

## License

- Main development kit: Apache License, Version 2.0
- See each package's README or [here](ros2_ws/src/kachaka_ros2_dev_kit/README.md#ライセンス) for details.

## Contribution

Contributions are welcome!  
- Bug reports: Open an issue in this repository.
- Bug fixes and features: Open a pull request, referencing related issues and providing test instructions/results.
- Documentation improvements: Typo fixes, clarifications, and additional information are appreciated.

See [CONTRIBUTING.md](external/kachaka-api/CONTRIBUTING.md) for more details.

## Acknowledgment

Some simulation assets are provided with the cooperation of Satsudora Holdings Co., Ltd. and EZOHUB TOKYO. See [kachaka_ros2_dev_kit/README.md](ros2_ws/src/kachaka_ros2_dev_kit/README.md#acknowledgment) for details.
