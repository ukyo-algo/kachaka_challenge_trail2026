from kachaka_utils.voice_manager import VoiceManager
from kachaka_interfaces.msg import ObjectDetection, ObjectDetectionListStamped

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time

# 検出を確定するまでの時間を定数として定義
REQUIRED_DURATION_SEC = 5.0

class WaitForHostReady:
    def __init__(self, parent_node: Node, voice_manager: VoiceManager):
        self.parent_node = parent_node
        self.voice_manager = voice_manager

        # 内部の状態変数
        self._is_running = False
        self._person_detected_start_time = None
        self._done_callback = None

        self.parent_node.create_subscription(
            ObjectDetectionListStamped,
            "/kachaka/object_detection/result",
            self._object_detection_callback,
            qos_profile_sensor_data,
        )
        
    def start(self, done_callback):
        """
        ホスト待機タスクを開始する。
        完了したら引数の done_callback(True) を呼び出す。
        """
        self.parent_node.get_logger().info("Starting WaitForHostReady task.")
        self.voice_manager.speak(f'準備ができたら、私の前に{int(REQUIRED_DURATION_SEC)}秒間立ってください。')
        
        # 状態をリセットして開始
        self._is_running = True
        self._person_detected_start_time = None
        self._done_callback = done_callback

    def cancel(self):
        """タスクを中断する"""
        self._is_running = False
        self.parent_node.get_logger().info("WaitForHostReady task cancelled.")

    def _object_detection_callback(self, detections: ObjectDetectionListStamped) -> None:
        # タスクが実行中でなければ何もしない
        if not self._is_running:
            return

        is_person_detected = any(
            obj.label == ObjectDetection.PERSON for obj in detections.detection
        )

        if is_person_detected:
            # 人を初めて検出した場合
            if self._person_detected_start_time is None:
                self.parent_node.get_logger().info("Person detected. Starting timer.")
                self.voice_manager.speak('認識しました。そのままお待ちください。')
                self._person_detected_start_time = self.parent_node.get_clock().now()
            # 人を検出し続けている場合
            else:
                elapsed = (self.parent_node.get_clock().now() - self._person_detected_start_time).nanoseconds / 1e9
                self.parent_node.get_logger().info(f"Person detected for {elapsed:.1f} seconds.", throttle_duration_sec=1.0)
                
                # 規定時間を超えたらタスク完了
                if elapsed >= REQUIRED_DURATION_SEC:
                    self.parent_node.get_logger().info("Host is ready. Task complete.")
                    self.voice_manager.speak('ありがとうございます。追従を開始します。')
                    
                    self._is_running = False # タスクを停止
                    if self._done_callback:
                        self._done_callback(True) # 完了を通知
        
        # 人が見えなくなった場合
        else:
            if self._person_detected_start_time is not None:
                self.parent_node.get_logger().info("Person lost. Resetting timer.")
                self.voice_manager.speak('認識が途切れました。もう一度お願いします。')
            self._person_detected_start_time = None

