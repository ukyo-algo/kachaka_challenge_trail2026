import rclpy
from kachaka_detect_person_interfaces.srv import PersonDetection
from rclpy.node import Node

class PDService(Node):
    def __init__(self):
        super().__init__("pd_service")
        self.srv = self.create_service(PersonDetection, 'person_detection', self.person_detection_callback)

    def person_detection_callback(self, request, response):
        response.front_image = request.front_image
        self.get_logger().info('Incoming request\na: %d b: %d' % (request.a, request.b))

        return response
    
def main(args=None):
    rclpy.init(args=args)

    pds = PDService()

    rclpy.spin(pds)

    rclpy.shutdown()


if __name__ == '__main__':
    main()