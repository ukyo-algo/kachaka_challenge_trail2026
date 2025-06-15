#!/usr/bin/env python3
import rclpy
import rclpy.logging
from rclpy.node import Node

from trail_kachaka_msgs.srv import ExampleHumanFollower
from kachaka_utils.voice_manager import VoiceManager
from kachaka_utils.nav_manager import NavManager
from trail_kachaka_example.some_sub_task1 import (
    ExampleSubTaskManager1,
)
from trail_kachaka_example.some_sub_task2 import (
    ExampleSubTaskManager2,
)

from trail_kachaka_example.llm_manager import LLMManager



class ExampleTaskManager(Node):
    def __init__(self) -> None:
        super().__init__("example_task_manager")

        self.voice_manager = VoiceManager(self)
        self.nav_manager = NavManager(self)
        self.subtask1 = ExampleSubTaskManager1(self.voice_manager, self.nav_manager)
        self.subtask2 = ExampleSubTaskManager2(self.voice_manager, self.nav_manager)
        self.llm_manager = LLMManager()
        self.human_follower_srv = self.create_client(
            ExampleHumanFollower, "example_human_follower_srv"
        )
        self.get_logger().info("ExampleTaskManager initialized.")

    def execute_task(self):
        self.voice_manager.speak("こんにちは、私はカチャカです。")
        if not self.nav_manager.go_to(x=0.0, y=0.0):
            self.get_logger().error("Failed to navigate to the initial position.")
            return

        success = self.subtask1.execute_sub_task1()
        if success:
            self.get_logger().info("Subtask 1 completed successfully.")
        else:
            self.subtask2.execute_sub_task2()

        res = self.exec_follow_srv()

        question = "What is the capital of Japan?"
        answer = self.llm_manager.infer(question)
        self.voice_manager.speak(f"I asked {question} and the answer was {answer}.")

        self.get_logger().info("I completed the task.")
        self.voice_manager.speak("タスクが完了しました。")

    def exec_follow_srv(self):
        self.get_logger().info("Sending follow request...")

        self.human_follower_srv.wait_for_service(timeout_sec=1.0)
        req = ExampleHumanFollower.Request()
        req.who_to_track = "David"
        req.distance = 0.5

        future = self.human_follower_srv.call_async(req)
        self.get_logger().info("Follow request sent.")
        rclpy.spin_until_future_complete(self, future)
        return future.result()


def main():
    rclpy.init()
    task_manager = ExampleTaskManager()

    try:
        task_manager.execute_task() 
    except KeyboardInterrupt:
        rclpy.logging.get_logger("executor").info(
            "Keyboard interrupt, shutting down..."
        )
    finally:
        task_manager.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
