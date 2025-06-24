import rclpy
import rclpy.logging
from rclpy.node import Node

from trail_kachaka_msgs.srv import ExampleHumanFollower


class ExampleHumanFollowerNode(Node):
    def __init__(self):
        super().__init__("example_human_follower_node")
        self.get_logger().info("ExampleNode has been started.")
        self.get_logger().debug("This is a debug message.")
        self.get_logger().warn("This is a warning message.")
        self.get_logger().error("This is an error message.")
        self.get_logger().fatal("This is a fatal message.")

        self.create_service(
            ExampleHumanFollower,
            "example_human_follower_srv",
            self.human_follower_callback,
        )

    def human_follower_callback(self, request, response):
        self.get_logger().info("Received request for human follower.")
        # Here you would implement the logic to follow a human
        # For now, we just log the request and return a success response
        response.success = True
        self.get_logger().info("Human follower task completed successfully.")
        return response
