import rclpy
from rclpy.node import Node
from kachaka_utils.position_helper import get_named_pose
from kachaka_utils.nav_manager import NavManager

class PartyTaskExecutor(Node):
    def __init__(self, nav_manager: NavManager):
        super().__init__('party_task_executor')
        self.state = 'go_to_host_room'
        self.nav_manager = nav_manager
        self.timer = self.create_timer(1.0, self._main_loop)

    def _main_loop(self):
        if self.state == 'go_to_host_room':
            self.get_logger().info("Going to host room...")
            pose = get_named_pose('host_room')
            self.nav_manager.go_to_pose(pose)  # 座標名 or PoseStamped
            self.state = 'wait_for_ready'

        


def main(args=None):
    rclpy.init(args=args)
    executor = PartyTaskExecutor()
    rclpy.spin(executor)
    rclpy.shutdown()


if __name__ == '__main__':
    main()