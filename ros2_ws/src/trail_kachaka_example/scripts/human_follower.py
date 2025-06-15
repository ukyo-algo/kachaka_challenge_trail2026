import rclpy
import rclpy.logging

from trail_kachaka_example.human_follower import (
    ExampleHumanFollowerNode,
)


def main():
    rclpy.init()
    example_node = ExampleHumanFollowerNode()

    try:
        rclpy.spin(example_node)
    except KeyboardInterrupt:
        rclpy.logging.get_logger("executor").info(
            "Keyboard interrupt, shutting down..."
        )
    finally:
        task_manager.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
