import time

from std_msgs.msg import Header
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, Pose, Point, Quaternion
from geometry_msgs.msg import PoseWithCovarianceStamped
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateThroughPoses, NavigateToPose

import rclpy

from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSReliabilityPolicy
from rclpy.qos import QoSProfile


class NavManager:
    def __init__(self, parent_node: Node):
        self.parent_node = parent_node
        self.initial_pose = Pose()
        self.goal_handle = None
        self.result_future = None
        self.feedback = None
        self.status: GoalStatus | None = None

        # --- 追加：現在のポーズを保持する変数を追加 ---
        self.current_pose: Pose | None = None

        amcl_pose_qos = QoSProfile(
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.initial_pose_received = False
        self.nav_through_poses_client = ActionClient(
            self.parent_node, NavigateThroughPoses, "navigate_through_poses"
        )
        self.nav_to_pose_client = ActionClient(
            self.parent_node, NavigateToPose, "navigate_to_pose"
        )
        self.model_pose_sub = self.parent_node.create_subscription(
            PoseWithCovarianceStamped,
            "amcl_pose",
            self._amcl_pose_callback,
            amcl_pose_qos,
        )
        self.initial_pose_pub = self.parent_node.create_publisher(
            PoseWithCovarianceStamped, "initialpose", 10
        )

    # --- 追加：現在の姿勢を取得するメソッド ---
    def get_current_pose_stamped(self) -> PoseStamped | None:
        """現在のロボットの姿勢をPoseStamped形式で取得する"""
        if self.current_pose is None:
            self.parent_node.get_logger().warn("Current pose is not available yet.")
            return None
        
        pose_stamped = PoseStamped()
        pose_stamped.header.stamp = self.parent_node.get_clock().now().to_msg()
        pose_stamped.header.frame_id = 'map'
        pose_stamped.pose = self.current_pose
        return pose_stamped


    def set_initial_pose(self, initial_pose: Pose):
        self.initial_pose_received = False
        self.initial_pose = initial_pose
        self._set_initial_pose()

    def go_through_poses(self, poses: list[PoseStamped]):
        # Sends a `NavToPose` action request and waits for completion
        self.debug("Waiting for 'NavigateToPose' action server")
        while not self.nav_through_poses_client.wait_for_server(timeout_sec=1.0):
            self.info("'NavigateToPose' action server not available, waiting...")

        goal_msg = NavigateThroughPoses.Goal()
        goal_msg.poses = poses

        self.info("Navigating with " + str(len(poses)) + " goals." + "...")
        send_goal_future = self.nav_through_poses_client.send_goal_async(
            goal_msg, self._feedback_callback
        )
        rclpy.spin_until_future_complete(self.parent_node, send_goal_future)
        self.goal_handle: NavigateThroughPoses.Result | None = send_goal_future.result()

        if not self.goal_handle:
            self.error("Goal handle is None")
            return False

        if not self.goal_handle.accepted:
            self.error("Goal with " + str(len(poses)) + " poses was rejected!")
            return False

        self.result_future = self.goal_handle.get_result_async()
        return True

    def go_to_pose_with_callback(self, pose: PoseStamped, done_callback):
        """
        非同期でナビゲーションを実行し、完了後
        に指定されたコールバック関数を呼び出す
        """
        self.debug("Waiting for 'NavigateToPose' action server")
        if not self.nav_to_pose_client.wait_for_server(timeout_sec=1.0):
            self.info("'NavigateToPose' action server not available.")
            # 失敗をコールバックに通知
            done_callback(None) 
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose

        self.info(f"Navigating to goal: {pose.pose.position.x}, {pose.pose.position.y}...")
        send_goal_future = self.nav_to_pose_client.send_goal_async(goal_msg, self._feedback_callback)

        # send_goal_futureが完了したら、_goal_sent_callbackを呼び出すように設定
        # done_callbackを部分適用（partial）のようにして渡す
        send_goal_future.add_done_callback(
            lambda future: self._goal_sent_callback(future, done_callback)
        )

    def _goal_sent_callback(self, future, done_callback):
        """ゴール送信後の処理"""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.error("Goal was rejected!")
            if done_callback:
                done_callback(None) # 失敗を通知
            return

        self.info("Goal accepted. Waiting for result...")
        result_future = goal_handle.get_result_async()
        
        # result_futureが完了したら、最終的なコールバックを呼び出す
        result_future.add_done_callback(
            lambda future: self._nav_result_callback(future, done_callback)
        )

    def _nav_result_callback(self, future, done_callback):
        """ナビゲーション完了時の最終的な処理"""
        result = future.result().result
        status = future.result().status
        if done_callback:
            # 成功/失敗のステータスをコールバックに渡す
            done_callback(status)

    def go_to_async(self, x: float, y: float, yaw: float = 0.0):
        pose = Pose(
            position=Point(x=x, y=y, z=0.0),
            orientation=Quaternion(
                x=0.0, y=0.0, z=yaw, w=1.0
            ),
        )
        pose_stamped = PoseStamped(
            pose=pose,
            header=Header(
                frame_id="map",
                stamp=self.parent_node.get_clock().now().to_msg(),
            )
        )
        return self.go_to_pose_async(pose_stamped)

    def go_to_pose_async(self, pose: PoseStamped):
        # Sends a `NavToPose` action request and waits for completion
        self.debug("Waiting for 'NavigateToPose' action server")
        while not self.nav_to_pose_client.wait_for_server(timeout_sec=1.0):
            print("c")
            self.info("'NavigateToPose' action server not available, waiting...")

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose

        self.info(
            "Navigating to goal: "
            + str(pose.pose.position.x)
            + " "
            + str(pose.pose.position.y)
            + "..."
        )
        send_goal_future = self.nav_to_pose_client.send_goal_async(
            goal_msg, self._feedback_callback
        )
        print("before")
        rclpy.spin_until_future_complete(self.parent_node, send_goal_future)
        print("after")
        self.goal_handle = send_goal_future.result()

        if not self.goal_handle.accepted:
            self.error(
                "Goal to "
                + str(pose.pose.position.x)
                + " "
                + str(pose.pose.position.y)
                + " was rejected!"
            )
            return False
        
        self.result_future = self.goal_handle.get_result_async()
        return True

    def go_to(self, x: float, y: float, yaw: float = 0.0):
        """Synchronous version of go_to that waits for navigation to complete"""
        if not self.go_to_async(x, y, yaw):
            return False

        while not self.is_nav_complete():
            rclpy.spin_once(self.parent_node, timeout_sec=0.1)

        return self.get_result() == GoalStatus.STATUS_SUCCEEDED

    def go_to_pose(self, pose: PoseStamped):
        print("a")
        """Synchronous version of go_to_pose that waits for navigation to complete"""
        if not self.go_to_pose_async(pose):
            print("False")
            return False
        print("b")
        while not self.is_nav_complete():
            print(self.is_nav_complete())
            rclpy.spin_once(self.parent_node, timeout_sec=0.1)

        return self.get_result() == GoalStatus.STATUS_SUCCEEDED

    def cancel_nav(self):
        self.info("Canceling current goal.")
        if self.result_future:
            future = self.goal_handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self.parent_node, future)
        return

    def is_nav_complete(self):
        if not self.result_future:
            # task was cancelled or completed
            return True
        rclpy.spin_until_future_complete(self.parent_node, self.result_future, timeout_sec=0.10)
        if self.result_future.result():
            self.status = self.result_future.result().status
            if self.status != GoalStatus.STATUS_SUCCEEDED:
                self.info("Goal with failed with status code: {0}".format(self.status))
                return True
        else:
            # Timed out, still processing, not complete yet
            return False

        self.info("Goal succeeded!")
        return True

    def get_feedback(self):
        return self.feedback

    def get_result(self):
        return self.status

    def wait_until_nav2_active(self):
        self._wait_for_node_to_activate("amcl")
        self._wait_for_initial_pose()
        self._wait_for_node_to_activate("bt_navigator")
        self.info("Nav2 is ready for use!")
        return

    def _wait_for_node_to_activate(self, node_name):
        # Waits for the node within the tester namespace to become active
        self.debug("Waiting for " + node_name + " to become active..")
        node_service = node_name + "/get_state"
        state_client = self.parent_node.create_client(GetState, node_service)
        while not state_client.wait_for_service(timeout_sec=1.0):
            self.info(node_service + " service not available, waiting...")

        req = GetState.Request()
        state = "unknown"
        while state != "active":
            self.debug("Getting " + node_name + " state...")
            future = state_client.call_async(req)
            rclpy.spin_until_future_complete(self.parent_node, future)
            if future.result() is not None:
                state = future.result().current_state.label
                self.debug("Result of get_state: %s" % state)
            time.sleep(2)
        return

    def _wait_for_initial_pose(self):
        while not self.initial_pose_received:
            self.info("Setting initial pose")
            self._set_initial_pose()
            self.info("Waiting for amcl_pose to be received")
            rclpy.spin_once(self.parent_node, timeout_sec=1)
        return

    # --- 修正：amcl_poseコールバックで現在の姿勢を保存 ---
    def _amcl_pose_callback(self, msg: PoseWithCovarianceStamped):
        """AMCLから送られてくる自己位置推定結果を保存する"""
        self.initial_pose_received = True
        self.current_pose = msg.pose.pose # PoseWithCovarianceからPoseを抽出して保存
        return
        
    def _feedback_callback(self, msg):
        self.feedback = msg.feedback
        print(self.feedback)
        return

    def _set_initial_pose(self):
        msg = PoseWithCovarianceStamped()
        msg.pose.pose = self.initial_pose
        msg.header.frame_id = "map"
        msg.header.stamp = self.parent_node.get_clock().now().to_msg()
        self.info("Publishing Initial Pose")
        self.initial_pose_pub.publish(msg)
        return

    def info(self, msg):
        self.parent_node.get_logger().info(msg)
        return

    def warn(self, msg):
        self.parent_node.get_logger().warn(msg)
        return

    def error(self, msg):
        self.parent_node.get_logger().error(msg)
        return

    def debug(self, msg):
        self.parent_node.get_logger().debug(msg)
        return
