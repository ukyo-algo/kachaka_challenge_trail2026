import rclpy
import rclpy.logging
from rclpy.executors import SingleThreadedExecutor

from kachaka_utils.src.kachaka_utils.speak import Speak
from kachaka_utils.src.kachaka_utils.nav_manager import NavManager

if __name__ == "__main__":
    rclpy.init()
    executor = SingleThreadedExecutor()

    speak_node = Speak()
    nav_node = NavManager()
    executor.add_node(nav_node)
    executor.add_node(speak_node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        rclpy.logging.get_logger("executor").info(
            "Keyboard interrupt, shutting down..."
        )
    finally:
        executor.shutdown()
        speak_node.destroy_node()
        nav_node.destroy_node()
        rclpy.shutdown()
