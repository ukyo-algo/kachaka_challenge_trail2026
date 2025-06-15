from kachaka_interfaces.action import ExecKachakaCommand
from kachaka_interfaces.msg import KachakaCommand
from rclpy.action import ActionClient
from rclpy.node import Node


class VoiceManager:
    def __init__(self, parent_node: Node) -> None:
        self._parent_node = parent_node
        self._action_client = ActionClient(
            self._parent_node, ExecKachakaCommand, "/kachaka/kachaka_command/execute"
        )
        self._action_client.wait_for_server()
        self._parent_node.get_logger().info("Speak action client is ready.")

    def speak(self, text: str, wait: bool = False):
        command = KachakaCommand()
        command.command_type = KachakaCommand.SPEAK_COMMAND
        command.speak_command_text = text
        goal_msg = ExecKachakaCommand.Goal()
        goal_msg.kachaka_command = command
        if wait:
            self._action_client.send_goal_async(goal_msg)
        else:
            self._action_client.send_goal(goal_msg)
