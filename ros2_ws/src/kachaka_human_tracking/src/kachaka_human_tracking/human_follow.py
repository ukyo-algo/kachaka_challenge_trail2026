import math
from collections import deque
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import Twist
from kachaka_interfaces.msg import ObjectDetection, ObjectDetectionListStamped
from sensor_msgs.msg import LaserScan
from std_srvs.srv import SetBool
from std_msgs.msg import Bool

# --- 追従パラメータ ---
SETPOINT_DISTANCE = 1.2  # 理想的な追従距離 (m)
FORWARD_SPEED_MAX = 0.3  # 最大前進速度 (m/s)
ANGULAR_SPEED_MAX = 0.8  # 最大旋回速度 (rad/s)

# --- 比例制御ゲイン (この値を調整して動きを滑らかにする) ---
KP_ANGULAR = 2.0  # 角度のズレに対するゲイン
KP_LINEAR = 1.5   # 距離のズレに対するゲイン

# --- 角度の許容範囲 (この範囲内なら前進を開始) ---
MOVE_START_ANGLE_THRESHOLD = 0.2  # (rad)

# --- 静止検出パラメータ ---
STOP_DETECTION_DURATION_SEC = 5.0  # 静止と判断するまでの秒数
STOP_DETECTION_THRESHOLD = 0.05    # 位置の標準偏差の閾値 (m)

class Follower(Node):
    def __init__(self) -> None:
        super().__init__("follow")

        # --- 状態変数 ---
        self._is_enabled = False
        self._host_stopped = False

        # --- 追従対象の位置情報 ---
        self._target_angle = 0.0
        self._target_distance = float("inf")
        self._person_detected = False

        # --- 静止検出用 ---
        history_size = int(STOP_DETECTION_DURATION_SEC / 0.1)
        self._position_history = deque(maxlen=history_size)

        # --- QoSプロファイル ---
        qos_profile = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=10)

        # --- ROS2コンポーネント ---
        self._vel_publisher = self.create_publisher(Twist, "/kachaka/manual_control/cmd_vel", 10)
        self._stopped_publisher = self.create_publisher(Bool, "/follower/host_stopped", 10)

        self.create_service(SetBool, "/follower/set_enabled", self._set_enabled_callback)
        self.create_subscription(
            ObjectDetectionListStamped, "/kachaka/object_detection/result", self._object_detection_callback, qos_profile
        )
        self.create_subscription(
            LaserScan, "/kachaka/lidar/scan", self._laser_scan_callback, qos_profile
        )

        # タイマーは__init__で一度だけ生成する
        self._timer = self.create_timer(0.1, self._control_loop)

    def _set_enabled_callback(self, request: SetBool.Request, response: SetBool.Response) -> SetBool.Response:
        """追従の有効/無効を切り替えるサービスコールバック"""
        self._is_enabled = request.data
        self.get_logger().info(f"Following enabled has been set to: {self._is_enabled}")

        if not self._is_enabled:
            # 停止が指示されたら、速度を0にし、状態をリセット
            self._stop_robot()
            self._host_stopped = False
            self._person_detected = False
            self._position_history.clear()

        # サービスが呼ばれるたびに履歴をクリア
        self._position_history.clear()
        response.success = True
        return response

    def _object_detection_callback(self, msg: ObjectDetectionListStamped) -> None:
        """人物を検出し、最も近い追跡対象の角度を特定する"""
        if not self._is_enabled:
            return

        persons = [obj for obj in msg.detection if obj.label == ObjectDetection.PERSON]

        if not persons:
            self._person_detected = False
            return

        # 最も近い人物を追跡対象とする
        persons.sort(key=lambda p: p.roi.pose.position.x**2 + p.roi.pose.position.y**2)
        closest_person = persons[0]

        # ターゲットの角度を計算 (x:前方, y:左方)
        pos = closest_person.roi.pose.position
        self._target_angle = math.atan2(pos.y, pos.x)
        self._person_detected = True

    def _laser_scan_callback(self, msg: LaserScan) -> None:
        """特定した人物の方向の正確な距離をLiDARから取得する"""
        #　Followerノードが呼ばれていない、またはターゲットが特定されていない場合
        if not self._is_enabled or not self._person_detected: 
            self._target_distance = float('inf')
            return
        
        # ターゲット角度に対応するLiDARのインデックスを計算
        try:
            index = int((self._target_angle - msg.angle_min) / msg.angle_increment)
        except ZeroDivisionError:
            return

        # 範囲外のインデックスを補正
        if not 0 <= index < len(msg.ranges):
            self._target_distance = float('inf')
            return

        # 狭い範囲の平均を取り、より安定した距離を算出する
        scan_range = 5  # 中心から左右いくつ分のデータを平均するか
        start_index = max(0, index - scan_range)
        end_index = min(len(msg.ranges) - 1, index + scan_range)

        valid_distances = [d for d in msg.ranges[start_index:end_index+1] if msg.range_min < d < msg.range_max]

        if valid_distances:
            self._target_distance = sum(valid_distances) / len(valid_distances)
            # 静止検出のために位置情報を記録
            pos_x = self._target_distance * math.cos(self._target_angle)
            pos_y = self._target_distance * math.sin(self._target_angle)
            self._position_history.append((pos_x, pos_y))
        else:
            self._target_distance = float('inf')

    def _check_for_stop_signal(self):
        """ホストの静止を検出する"""
        if len(self._position_history) < self._position_history.maxlen:
            return

        positions = np.array(self._position_history)
        std_dev = np.std(positions, axis=0)

        if np.all(std_dev < STOP_DETECTION_THRESHOLD):
            if not self._host_stopped:
                self.get_logger().info('Host has stopped. Stopping follow.')
                self._host_stopped = True
                msg = Bool()
                msg.data = True
                self._stopped_publisher.publish(msg)

    def _control_loop(self) -> None:
        """速度指令をPublishするメインループ"""
        if not self._is_enabled or self._host_stopped or not self._person_detected:
            self._stop_robot()
            return

        self._check_for_stop_signal()
        if self._host_stopped:
            self._stop_robot()
            return

        cmd_vel = Twist()
        distance_error = self._target_distance - SETPOINT_DISTANCE

        # 1. 旋回制御（向きを合わせる）
        angular_vel = self._target_angle * KP_ANGULAR
        cmd_vel.angular.z = np.clip(angular_vel, -ANGULAR_SPEED_MAX, ANGULAR_SPEED_MAX)

        # 2. 前後進制御（距離を合わせる）
        # ターゲットがほぼ正面にいる場合のみ前進する
        if abs(self._target_angle) < MOVE_START_ANGLE_THRESHOLD:
            linear_vel = distance_error * KP_LINEAR
            cmd_vel.linear.x = np.clip(linear_vel, -FORWARD_SPEED_MAX, FORWARD_SPEED_MAX)
        else:
            cmd_vel.linear.x = 0.0 # 向きがずれている場合は、まずその場で回転する

        self._vel_publisher.publish(cmd_vel)
        self.get_logger().info(f"Target at D={self._target_distance:.2f}m, A={self._target_angle:.2f}rad -> V={cmd_vel.linear.x:.2f}, W={cmd_vel.angular.z:.2f}", throttle_duration_sec=1)

    def _stop_robot(self):
        """ロボットを確実に停止させる"""
        cmd_vel = Twist()
        self._vel_publisher.publish(cmd_vel)

        
