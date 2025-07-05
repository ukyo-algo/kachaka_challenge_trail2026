import math
from collections import deque
import numpy as np
from enum import Enum

import angles
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import Twist
from kachaka_interfaces.msg import ObjectDetection, ObjectDetectionListStamped
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_srvs.srv import SetBool
from std_msgs.msg import Bool
# --- 追加：音声再生のためにインポート ---
from kachaka_utils.voice_manager import VoiceManager

# --- 追従パラメータ ---
MAX_RANGE_FOR_FOLLOW = 2
ANGULAR_TOLERANCE = 0.3

# --- 静止検出パラメータ ---
STOP_DETECTION_DURATION_SEC = 10 #何秒間の静止で停止と判断するか
STOP_DETECTION_THRESHOLD = 0.05  #位置の標準偏差の閾値
# --- 追加：人間確認のためのパラメータ ---
CONFIRMATION_TIMEOUT_SEC = 15.0 # 確認モードのタイムアウト時間
CONFIRMATION_MOVE_THRESHOLD = 0.1 # この値以上動いたら「反応あり」と判断

# --- 追加：Followerの状態を定義するEnum ---
class FollowerState(Enum):
    IDLE = 0             # 待機中
    FOLLOWING = 1        # 追跡中
    CONFIRMING_STOP = 2  # 停止確認中

class Follower(Node):
    def __init__(self) -> None:
        super().__init__("follow")

        # --- 状態変数 ---
        self._state = FollowerState.IDLE
        self._person_in_detection = False

        # --- 追従対象の位置情報 ---
        self._closest_distance = float("inf")
        self._closest_angle = 0.0

        # --- 追跡用の履歴 ---
        self.previous_turn = ""

        # --- 追加：音声マネージャーの初期化 ---
        self.voice_manager = VoiceManager(self)

        # --- QoSプロファイル ---
        qos_profile = QoSProfile(
            reliability = ReliabilityPolicy.BEST_EFFORT,
            depth = 10
        )

        # --- ROS2コンポーネント ---
        self._publisher = self.create_publisher(
            Twist, "/kachaka/manual_control/cmd_vel", 10
        )
        self._lidar_subscriber = self.create_subscription(
            LaserScan, "/kachaka/lidar/scan", self._laser_scan_callback, qos_profile
        )
        self._object_detection_subscriber = self.create_subscription(
            ObjectDetectionListStamped,
            "/kachaka/object_detection/result",
            self._object_detection_callback,
            qos_profile,
        )
        self._stopped_publisher = self.create_publisher(
            Bool, "/follower/host_stopped", 10
        ) #ホストが止まったかどうかをpublishする
        self.create_service(
            SetBool, "/follower/set_enabled", self._set_enabled_callback
        ) #追跡を開始するかどうかを受け取り、追跡を開始する

        #-- 静止検出用変数 --
        self.history_size = int(STOP_DETECTION_DURATION_SEC/ 0.1)
        self._position_history = deque(maxlen=self.history_size)

        # --- 追加：確認モード用のタイマー ---
        self._confirmation_timer = None

    def _set_enabled_callback(self, request: SetBool.Request, response: SetBool.Response) -> SetBool.Response:
        """追跡の有効/無効を切り替えるサービスコールバック"""
        if request.data:
            self.get_logger().info("Following enabled. Starting main loop.")
            self._state = FollowerState.FOLLOWING
            self.voice_manager().speak("追従を開始します。パーティー会場まで歩いてください。到着したら10秒間止まってください。")
            self._person_in_detection = False
            self._position_history.clear()
            # 0.1秒ごとにメインループ(_publish_cmd_vel)を実行するタイマーを開始
            self._timer = self.create_timer(0.1, self._publish_cmd_vel)
        else:
            self.get_logger().info("Following disabled.")
            self._state = FollowerState.IDLE
            self.voice_manager().speak("追従を停止します。")
            self._stop_robot()
            if self._timer and not self._timer.is_canceled():
                self._timer.cancel()
            if self._confirmation_timer and not self._confirmation_timer.is_canceled():
                self._confirmation_timer.cancel()

        response.success = True
        return response

    def _object_detection_callback( self, detections: ObjectDetectionListStamped ) -> None:
        """人物検出コールバック"""
        if self._state == FollowerState.IDLE:
            return

        is_person_found = any(
            obj.label == ObjectDetection.PERSON for obj in detections.detection
        )

        if is_person_found and not self._person_in_detection:
            self.get_logger().info('Person detected for the first time.')
            self._position_history.clear()
            self._person_in_detection = True

        """elif not is_person_found and self._person_in_detection:
            self.get_logger().info('Person lost.')
            self._person_in_detection = False"""

    def _laser_scan_callback(self, msg: LaserScan) -> None:
        """LiDARデータから最近傍物体を検出"""
        if self._state == FollowerState.IDLE:
            return

        # 人物が検出されていない場合は追跡しない
        if not self._person_in_detection:
            self._closest_distance = float('inf')
            return
        ranges = msg.ranges
        #正面方向の範囲に切り取る
        valid_ranges = ranges[int((math.pi/2-ANGULAR_TOLERANCE)/msg.angle_increment):int((math.pi/2+ANGULAR_TOLERANCE)/msg.angle_increment)]
        #self.get_logger().info(str(len(ranges))+" "+str(msg.angle_increment)+" "+str(msg.angle_min)+" "+str(msg.angle_max))
        valid_ranges = [r for r in valid_ranges if r > 0]
        #self.get_logger().info(str(len(valid_ranges)))
        if not valid_ranges:
            self._target_distance = float("inf")
            return

        min_range = min(valid_ranges)
        min_index = ranges.index(min_range)
        angle_increment = msg.angle_increment
        self._closest_distance = min_range
        self._closest_angle = angles.normalize_angle(
            msg.angle_min + (min_index * angle_increment) + (math.pi / 2)
        )
        # 静止検出のために、極座標系からロボットを中心とした直交座標系に変換
        pos_x = self._closest_distance * math.cos(self._closest_angle)
        pos_y = self._closest_distance * math.sin(self._closest_angle)
        self._position_history.append((pos_x, pos_y))
            
    def _publish_cmd_vel(self) -> None:
        """状態に応じて速度指令をPublishするメインループ"""
        if self._state == FollowerState.FOLLOWING:
            self._execute_following()
        elif self._state == FollowerState.CONFIRMING_STOP:
            self._execute_confirmation()
        else: # IDLE
            self._stop_robot()

    def _execute_following(self):
        """追跡を実行する"""
        # 人がいない、または遠すぎる場合は停止
        if not self._person_in_detection :
            self._stop_robot()
            return

        #-- 静止検出 --
        self._check_for_stop_signal()

        #-- 追跡 --
        self.get_logger().info("publish")
        self.get_logger().info(f"{self._closest_angle=}, {self._closest_distance=}")
        cmd_vel = Twist()
        # if 0.3 < self._closest_angle < ANGULAR_TOLERANCE:
        if self._closest_distance > MAX_RANGE_FOR_FOLLOW :
            if self.previous_turn == "left":
                self.get_logger().info("turn left")
                cmd_vel.angular.z = -1.0
            elif self.previous_turn == "right":
                self.get_logger().info("turn right")
                cmd_vel.angular.z = 1.0
            else :
                self.get_logger().info("go forward")
                cmd_vel.linear.x = 0.5
        else :
            cmd_vel.linear.x = 0.4
            cmd_vel.angular.z = self._closest_angle*3
            if 0.0 < self._closest_angle:
                self.get_logger().info("turn right")
                self.previous_turn = "right"
            # elif -0.3 > self._closest_angle > -ANGULAR_TOLERANCE:
            elif -0.0 > self._closest_angle:
                self.get_logger().info("turn left")
                self.previous_turn = "left"
            else :
                self.previous_turn = ""
        """if 0.3 < self._closest_angle:
            self.get_logger().info("turn right")
            cmd_vel.angular.z = 1.0 #self._closest_angle*2
        # elif -0.3 > self._closest_angle > -ANGULAR_TOLERANCE:
        elif -0.3 > self._closest_angle:
            self.get_logger().info("turn left")
            cmd_vel.angular.z = -1.0"""
        # elif 0.15 < self._closest_angle < ANGULAR_TOLERANCE:
        # elif 0.3 < self._closest_angle:
        #     self.get_logger().info("turn right")
        #     self.previous_turn = "right"
        #     cmd_vel.angular.z = self._closest_angle*2
        # # elif -0.3 > self._closest_angle > -ANGULAR_TOLERANCE:
        # elif -0.3 > self._closest_angle:
        #     self.get_logger().info("turn left")
        #     self.previous_turn = "left"
        #     cmd_vel.angular.z = -self._closest_angle*2
        # # elif 0.15 < self._closest_angle < ANGULAR_TOLERANCE:
        # else :
        #     self.previous_turn = ""
        #     if 0.15 < self._closest_angle:
        #         cmd_vel.linear.x = 0.3
        #         cmd_vel.angular.z = 0.4
        #     # elif -0.15 > self._closest_angle > -ANGULAR_TOLERANCE:
        #     elif -0.15 > self._closest_angle:
        #         cmd_vel.linear.x = 0.3
        #         cmd_vel.angular.z = -0.4
        #     elif self._closest_angle > ANGULAR_TOLERANCE or self._closest_angle < -ANGULAR_TOLERANCE:
        #         cmd_vel.linear.x = 0.0
        #         cmd_vel.angular.z = 0.0   
        #     else:
        #         self.get_logger().info("go foward")
        #         cmd_vel.linear.x = self._closest_distance*1.5
        self._publisher.publish(cmd_vel)

    def _check_for_stop_signal(self):
        """ホストの静止を検出し、確認モードへ移行する"""
        if len(self._position_history) < self.history_size:
            return
        #x,y座標の標準偏差を計算
        positions = np.array(self._position_history)
        std_dev = np.std(positions, axis=0)
        #x,y座標のばらつきが閾値以下なら静止と判断
        if np.all(std_dev < STOP_DETECTION_THRESHOLD):
            self.get_logger().info('Potential stop detected. Entering confirmation mode.')
            self._state = FollowerState.CONFIRMING_STOP
            self._stop_robot()
            # 確認用のタイマーを開始
            self._confirmation_timer = self.create_timer(CONFIRMATION_TIMEOUT_SEC, self._on_confirmation_timeout)
            # 音声で呼びかけ
            self.voice_manager.speak("到着しましたか。到着したら動かないでください。到着してなければ近くに来てください")
            # 確認期間中の動きを検出するため、履歴をクリア
            self._position_history.clear()

    def _execute_confirmation(self):
        """確認モードの処理。相手の反応（動き）を監視する。"""
        self._stop_robot() # 確認中は停止

        if len(self._position_history) < self.history_size / 2: # 少しデータが溜まるまで待つ
            return

        positions = np.array(self._position_history)
        std_dev = np.std(positions, axis=0)

        # もし対象が動いたら（反応があったら）、追跡を再開
        if np.any(std_dev > CONFIRMATION_MOVE_THRESHOLD):
            self.get_logger().info("Movement detected! Resuming following.")
            self._state = FollowerState.FOLLOWING
            if self._confirmation_timer and not self._confirmation_timer.cancel:
                self._confirmation_timer.cancel()
            self._position_history.clear()

    def _on_confirmation_timeout(self):
        """確認がタイムアウトした時の処理（人間が静止し続けた場合）"""
        self.get_logger().info('Confirmation timed out. Assuming host has stopped.')
        self._state = FollowerState.IDLE # タスク完了
        if self._confirmation_timer and not self._confirmation_timer.is_canceled():
            self._confirmation_timer.cancel()
        
        # Executorにホストが停止したことを通知
        msg = Bool()
        msg.data = True
        self._stopped_publisher.publish(msg)
        
        # メインループを停止
        if self._timer and not self._timer.is_canceled():
            self._timer.cancel()


    def _stop_robot(self):
        """ロボットを確実に停止させる"""
        cmd_vel = Twist()
        self._publisher.publish(cmd_vel)
