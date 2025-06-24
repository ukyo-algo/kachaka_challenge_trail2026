USER_ID ?= $(shell id -u)
GROUP_ID ?= $(shell id -g)
REAL_IP ?=

.PHONY: build
build: build-bridge build-app

.PHONY: build-app
build-app:
	docker build \
		-t weblab/v1-kachaka-jazzy \
		--build-arg USER_ID="$(USER_ID)" \
		--build-arg GROUP_ID="$(GROUP_ID)" \
		-f ./docker/Dockerfile \
		.

.PHONY: build-bridge
build-bridge:
	docker buildx build \
		-t kachaka-api \
		--target kachaka-grpc-ros2-bridge \
		-f ./external/kachaka-api/Dockerfile.ros2 \
		--build-arg BASE_ARCH=x86_64 \
		--load \
		./external/kachaka-api

.PHONY: start-bridge
start-bridge:
	@if [ -z "$(REAL_IP)" ]; then \
		echo "Error: REAL_IP not specified. Use: make start-bridge REAL_IP=192.168.x.x"; \
		exit 1; \
	fi
	@echo "Starting ROS2 bridge to real Kachaka at $(REAL_IP)..."
	@USER_ID=$(USER_ID) GROUP_ID=$(GROUP_ID) API_GRPC_BRIDGE_SERVER_URI="$(REAL_IP):26400" NAMESPACE=kachaka FRAME_PREFIX="" \
		docker compose -f ./external/kachaka-api/tools/ros2_bridge/docker-compose.yaml up -d ros2_bridge || { \
		echo "Failed to start ROS2 bridge. Please check the IP address and try again."; \
		exit 1; \
	}

.PHONY: stop-bridge
stop-bridge:
	@echo "Stopping ROS2 bridge..."
	@docker compose -f ./external/kachaka-api/tools/ros2_bridge/docker-compose.yaml down ros2_bridge || true


.PHONY: clean
clean:
	rm -rf ros2_ws/build
	rm -rf ros2_ws/install
	rm -rf ros2_ws/log
