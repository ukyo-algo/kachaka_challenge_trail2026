import rclpy
from rclpy.node import Node
from kachaka_detect_person_interfaces.srv import PersonDetection
import sys

class PDClient(Node):
    def __init__(self):
        super().__init__("pd_client_async")
        self.client=self.create_client(PersonDetection,"person_detection")
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req=PersonDetection.request()