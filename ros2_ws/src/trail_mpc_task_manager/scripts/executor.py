#!/usr/bin/env python3

from kachaka_utils.position_helper import get_named_pose
from kachaka_utils.nav_manager import NavManager
from kachaka_utils.voice_manager import VoiceManager
from kachaka_utils.llm_manager import LLMManager
from kachaka_utils.camera_manager import CameraManager
from trail_mpc_task_manager.wait_for_ready import WaitForReady
from trail_mpc_task_manager.guest_meet_task import GuestMeetTaskManager
from trail_mpc_task_manager import FindEmptyChairTaskManager

import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
from std_msgs.msg import Bool
from geometry_msgs.msg import PoseStamped
from action_msgs.msg import GoalStatus
# --- 追加：時間（Duration）を扱うためにインポート ---
from rclpy.duration import Duration

# --- 追加：位置情報取得のための再試行パラメータ ---
POSE_RETRY_TIMEOUT_SEC = 5.0  # 最大5秒間、再試行する
POSE_RETRY_INTERVAL_SEC = 0.2 # 0.2秒間隔で再試行する



class PartyTaskExecutor(Node):
    def __init__(self):
        super().__init__('party_task_executor')
        self.state = 'go_to_host_room'
        self.nav_manager = NavManager(self)
        self.voice_manager = VoiceManager(self)
        self.camera_manager = CameraManager(self)
        self.llm_manager = LLMManager()
        self.wait_state = WaitForReady(self,self.voice_manager)
        self.guest_meet_task = GuestMeetTaskManager(self,camera_manager, self.voice_manager, self.llm_manager)
        self.find_empty_chair = FindEmptyChairTaskManager(self, self.camera_manager, self.voice_manager, self.llm_manager)

        # --- 追加：ホストが停止した最後の場所を保存する変数 ---
        self.last_known_host_pose: PoseStamped | None = None

        #--- followノード制御用のクライアントとサブスクライバー ---
        self._set_follow_client = self.create_client(SetBool, "/follower/set_enabled")
        self.get_logger().info("Waiting for /follower/set_enabled service...")
        self._set_follow_client.wait_for_service()
        self.get_logger().info("Service found.")

        self._stop_follower_subscriber = self.create_subscription(
            Bool, "/follower/host_stopped", self._host_stopped_callback, 10
        )
        self._follow_started = False

    def start_mission(self):
        """ミッションを開始する"""
        self.get_logger().info("Mission start!")
        self._execute_go_to_host_room()
    
    def _execute_go_to_host_room(self):
        """ホストの部屋へ移動するタスクを開始"""
        self.state = 'go_to_host_room'
        self.get_logger().info("State: go_to_host_room. Executing navigation.")
        pose = get_named_pose('host_room')
        # 完了後のコールバック関数として _on_nav_done_to_host_room を渡す
        self.nav_manager.go_to_pose_with_callback(pose, self._on_nav_done_to_host_room)

    def _on_nav_done_to_host_room(self, status):
        """ホストの部屋へのナビゲーション完了時の処理"""
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info("Navigation to host room succeeded.")
            self._execute_wait_for_host_ready()
        else:
            self.get_logger().error(f"Navigation to host room failed with status: {status}")
            self._handle_mission_failure("ナビゲーションに失敗しました。")
    
    def _execute_wait_for_host_ready(self):
        """ホストの準備を待つタスクを開始"""
        self.state = 'wait_for_host_ready'
        self.get_logger().info("State: wait_for_host_ready")
        # 完了時に _on_host_ready_done を呼び出すように設定してタスクを開始
        self.wait_state.start(done_callback=self._on_host_ready_done) 
        # 60秒のタイムアウトを設定
        self.timeout_timer = self.create_timer(60.0, self._wait_for_host_timeout)
    
    def _on_host_ready_done(self, success: bool):
        """WaitForReadyタスク完了時のコールバック"""
        if success:
            self.get_logger().info("Host is ready. Proceeding to follow_host.")
            self.voice_manager.speak('ありがとうございます。準備が確認できました。')
            self._execute_follow_host()
        else:
            # 失敗した場合の処理
            self.get_logger().error("WaitForHostReady task failed or timed out.")
            self._handle_mission_failure("ホストの準備を確認できませんでした。")

    def _wait_for_host_timeout(self):
        """wait_for_hostのタイムアウト時に実行される"""
        # タイムアウトタイマーを破棄
        if self.timeout_timer:
            self.timeout_timer.cancel()
            self.timeout_timer.destroy()

        # 状態がまだ wait_for_host_ready の場合のみタイムアウト処理を実行
        if self.state == 'wait_for_host_ready':
            self.get_logger().error("Timeout: Host did not appear in time.")
            self.wait_state.cancel() # 進行中のタスクを中断させる
            self._handle_mission_failure("時間内にホストを認識できませんでした。")
        
    def _execute_follow_host(self):
        """ホストの追従タスクを開始"""
        self.state = 'follow_host'
        self.get_logger().info('State: follow_host. Starting...')
        self._set_following_enabled(True)
        self._follow_started = True

    def _set_following_enabled(self, enabled: bool):
        """追従ノードの有効/無効をリクエストする"""
        req = SetBool.Request()
        req.data = enabled
        future = self._set_follow_client.call_async(req)
        self.get_logger().info(f"Requested to set following to {enabled}.")
    
    def _host_stopped_callback(self, msg: Bool):
        """追従停止の通知を受け取るコールバック"""
        if self.state == 'follow_host' and msg.data:
            self.get_logger().info("Stop signal received from follower node.")
            # 1. 追従を正式に停止させる
            self._set_following_enabled(False)
            # 2. 現在地を再試行ロジックで確実に取得する
            self.get_logger().info(f"Attempting to get current pose (timeout: {POSE_RETRY_TIMEOUT_SEC}s)...")
            start_time = self.get_clock().now()
            timeout = Duration(seconds=POSE_RETRY_TIMEOUT_SEC)
            # タイムアウトするまで位置情報の取得を試みる
            while self.get_clock().now() - start_time < timeout:
                self.last_known_host_pose = self.nav_manager.get_current_pose_stamped()
                if self.last_known_host_pose is not None:
                    # 取得に成功したらループを抜ける
                    break
                
                self.get_logger().info("Pose not available yet, retrying...")
                # 短い待機時間を入れて、他の処理（AMCLのコールバックなど）を許可する
                rclpy.spin_once(self, timeout_sec=POSE_RETRY_INTERVAL_SEC)
            if self.last_known_host_pose:
                pos = self.last_known_host_pose.pose.position
                self.get_logger().info(f"Host stopped. Location saved: x={pos.x}, y={pos.y}")
                self.voice_manager.speak("玄関に戻ってゲストをお連れします")
            else:
                self.get_logger().error("Failed to get current pose. Cannot save host location.")
                self._handle_mission_failure("現在位置の取得に失敗しました。")
                return
            # 3. 次のタスク（玄関への移動）を実行
            self._execute_go_to_entrance()

    def _execute_go_to_entrance(self):
        """玄関へ移動するタスク"""
        self.state = 'go_to_entrance'
        self.get_logger().info("State: go_to_entrance")
        # 同様にナビゲーションを実行
        pose = get_named_pose('entrance')
        self.nav_manager.go_to_pose_with_callback(pose, self._on_nav_done_to_entrance)

    def _on_nav_done_to_entrance(self, status):
        """玄関へのナビゲーション完了時の処理"""
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info("Navigation to entrance succeeded.")
            self._execute_wait_for_guest_ready()
        else:
            self.get_logger().error(f"Navigation to entrance failed with status: {status}")
            self._handle_mission_failure("ナビゲーションに失敗しました。")

    def _execute_wait_for_guest_ready(self):
        """ゲストの準備ができたか確認する関数"""
        self.state = 'wait_for_guest_ready'
        self.get_logger().info("State: wait_for_guest_ready")
        # 完了時に _on_guest_ready_done を呼び出すように設定してタスクを開始
        self.wait_state.start(done_callback=self._on_guest_ready_done) 
        # 60秒のタイムアウトを設定
        self.timeout_timer = self.create_timer(60.0, self._wait_for_guest_timeout)

    def _on_guest_ready_done(self, success: bool):
        """ゲストのWaitForReadyタスク完了時のコールバック"""
        if success:
            self.get_logger().info("Guest is ready. Execute guest_meet_task.")
            if self.guest_meet_task.execute_guest_meet():
                self._execute_return_to_host()
        else:
            # 失敗した場合の処理
            self.get_logger().error("WaitForReady task failed or timed out.")
            self._handle_mission_failure("ゲストの準備を確認できませんでした。")

    def _wait_for_guest_timeout(self):
        """wait_for_guestのタイムアウト時に実行される"""
        # タイムアウトタイマーを破棄
        if self.timeout_timer:
            self.timeout_timer.cancel()
            self.timeout_timer.destroy()

        # 状態がまだ wait_for_host_ready の場合のみタイムアウト処理を実行
        if self.state == 'wait_for_guest_ready':
            self.get_logger().error("Timeout: Guest did not appear in time.")
            self.wait_state.cancel() # 進行中のタスクを中断させる
            self._handle_mission_failure("時間内にゲストを認識できませんでした。")


    def _execute_return_to_host(self):
        """保存したホストの場所に戻る"""
        self.state = 'return_to_host'
        self.get_logger().info("State: return_to_host")
        if self.last_known_host_pose:
            self.get_logger().info("Returning to the last known host location.")
            self.voice_manager.speak("パーティー会場にお連れします")
            self.nav_manager.go_to_pose_with_callback(self.last_known_host_pose, self._on_nav_done_to_return)
        else:
            self.get_logger().error("No host location saved. Cannot return.")
            self._handle_mission_failure("ホストの場所が保存されていません。")

    def _on_nav_done_to_return(self, status):
        """戻るナビゲーションが完了したときの処理"""
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info("Successfully returned to host's location.")
            self.voice_manager.speak("パーティー会場に到着しました。")
            self._execute_find_empty_chair()
        else:
            self.get_logger().error("Failed to return to host's location.")
            self._handle_mission_failure("元の場所に戻れませんでした。")

    def _execute_find_empty_chair(self):
        """ゲストに空いている席を示す"""
        self.state = 'find_empty_chair'
        self.get_logger().info("State: find_empty_chair")
        self.find_empty_chair.execute_find_empty_chair()
        self._execute_go_to_entrance()


    def _handle_mission_failure(self, reason: str):
        self.get_logger().error(f"MISSION FAILED: {reason}")
        self.voice_manager.speak(f"ミッションに失敗しました。理由は、{reason}です。")
    
        # 状態に応じたリカバリー処理
        if self.state == 'go_to_host_room':
            self.nav_manager.cancel_nav()    
            self.voice_manager.speak("ホストの部屋に到達できませんでした。再試行します。")
            self._execute_go_to_host_room()
        if self.state == 'wait_for_host_ready':
            self.wait_state.cancel()    
            self.voice_manager.speak("タスクを再実行します")
            self._execute_wait_for_host_ready()
        if self.state == 'go_to_entrance':
            self.nav_manager.cancel_nav() 
            self.voice_manager.speak("玄関に到達できませんでした。再試行します")
            self._execute_go_to_entrance()
        if self.state == 'wait_for_guest_ready':
            self.wait_state.cancel()
            self.voice_manager.speak("タスクを再実行します")
            self._execute_wait_for_guest_ready()
        if self.state == 'return_to_host':
            if reason == "ホストの場所が保存されていません。":
                self.voice_manager("タスクを中止します")
            else:  
                self.voice_manager('タスクを再実行します。')
                self._execute_return_to_host()

            

        


def main(args=None):
    rclpy.init(args=args)
    executor = PartyTaskExecutor()
    # ミッションを開始
    #executor.start_mission()
    executor._execute_follow_host()
    rclpy.spin(executor)
    executor.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()