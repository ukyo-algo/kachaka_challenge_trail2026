#!/usr/bin/env python3
"""
Task 3 自動採点ノード

学習者が /task3/found_garbage に FoundGarbage メッセージを送ると、
このノードが受信して結果を表示・採点します。

【学習者がやること】
1. 地図全体を自律探索する戦略を実装する
2. カメラ画像で YOLO を使ってゴミ（bottle/cup/can）を検出・分類する
3. 検出したら /task3/found_garbage に FoundGarbage を publish する

【このノードがやること】
- /task3/found_garbage を受信して内容を表示
- 送られてきた画像をウィンドウに表示（image.data が空でなければ）
- 発見数・分類数とスコアをログに出力
- /task3_judge/status に JSON 形式でスコアを配信

【採点】
発見スコア = 発見数 × 10 点
分類スコア = 正しく分類した数 × 5 点（正解クラスは非公開のため自己評価）
重複チェック: 2.0m 以内の再送は無視
"""

import json
import math

import numpy as np

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from trail_kachaka_msgs.msg import FoundGarbage

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

DUPLICATE_THRESHOLD = 2.0
VALID_CLASSES = {'bottle', 'cup', 'can'}


class Task3Judge(Node):
    def __init__(self):
        super().__init__('task3_judge')
        self.found_items = []

        self.create_subscription(
            FoundGarbage, '/task3/found_garbage', self._callback, 10
        )
        self.status_pub = self.create_publisher(String, '/task3_judge/status', 10)
        self.create_timer(10.0, self._report_timer)

        self.get_logger().info('=' * 55)
        self.get_logger().info(' Task 3 Judge 起動完了 — 完全探索・分類チャレンジ')
        self.get_logger().info(' 以下のトピックにゴミ発見情報を送信してください:')
        self.get_logger().info('   /task3/found_garbage  (trail_kachaka_msgs/FoundGarbage)')
        self.get_logger().info(' 有効クラス: bottle / cup / can')
        self.get_logger().info('=' * 55)

    def _callback(self, msg: FoundGarbage):
        if msg.garbage_class not in VALID_CLASSES:
            self.get_logger().warn(
                f'[無効] garbage_class="{msg.garbage_class}" は認識できません。'
                f'有効: {VALID_CLASSES}'
            )
            return

        if self._is_duplicate(msg.robot_x, msg.robot_y):
            self.get_logger().warn(
                f'[重複] ({msg.robot_x:.1f}, {msg.robot_y:.1f}) は既存の発見と近すぎます。スキップ。'
            )
            return

        item = {
            'id': len(self.found_items) + 1,
            'class': msg.garbage_class,
            'confidence': round(float(msg.confidence), 3),
            'x': round(float(msg.robot_x), 2),
            'y': round(float(msg.robot_y), 2),
        }
        self.found_items.append(item)

        score = len(self.found_items) * 10
        self.get_logger().info(
            f'[発見 #{item["id"]}] {item["class"]} '
            f'(信頼度: {item["confidence"]:.1%}) '
            f'at ({item["x"]:.1f}, {item["y"]:.1f}) | 発見スコア: {score}点'
        )

        self._try_show_image(msg, item)
        self._publish_status()

    def _is_duplicate(self, x: float, y: float) -> bool:
        for item in self.found_items:
            dist = math.sqrt((item['x'] - x) ** 2 + (item['y'] - y) ** 2)
            if dist < DUPLICATE_THRESHOLD:
                return True
        return False

    def _try_show_image(self, msg: FoundGarbage, item: dict):
        if not CV2_AVAILABLE or len(msg.image.data) == 0:
            return
        try:
            np_arr = np.frombuffer(bytes(msg.image.data), np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is not None:
                label = f'#{item["id"]}: {item["class"]} ({item["confidence"]:.0%})'
                cv2.putText(img, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                cv2.imshow(f'Task3 Judge — 発見 #{item["id"]}', img)
                cv2.waitKey(1)
        except Exception as e:
            self.get_logger().warn(f'画像表示エラー: {e}')

    def _report_timer(self):
        counts = {'bottle': 0, 'cup': 0, 'can': 0}
        for item in self.found_items:
            counts[item['class']] = counts.get(item['class'], 0) + 1
        self.get_logger().info(
            f'現在の発見: bottle={counts["bottle"]}, '
            f'cup={counts["cup"]}, can={counts["can"]} '
            f'(計 {len(self.found_items)} 個)'
        )

    def _publish_status(self):
        counts = {}
        for item in self.found_items:
            counts[item['class']] = counts.get(item['class'], 0) + 1
        status = {
            'task': 3,
            'found': len(self.found_items),
            'by_class': counts,
            'score': len(self.found_items) * 10,
            'items': self.found_items,
        }
        msg = String()
        msg.data = json.dumps(status, ensure_ascii=False)
        self.status_pub.publish(msg)


def main():
    rclpy.init()
    node = Task3Judge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
