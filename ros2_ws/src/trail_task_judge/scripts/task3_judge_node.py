#!/usr/bin/env python3
"""
Task 3 自動採点ノード

/task3/found_garbage に FoundGarbage メッセージが届いたら
内容をログに表示し、画像があればウィンドウに表示します。
"""

import json
from datetime import datetime
from pathlib import Path

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

VALID_CLASSES = {'bottle', 'cup', 'can'}
SAVE_DIR = Path('/app/judge_results/task3')


class Task3Judge(Node):
    def __init__(self):
        super().__init__('task3_judge')
        self.received: list[dict] = []
        SAVE_DIR.mkdir(parents=True, exist_ok=True)

        self.create_subscription(
            FoundGarbage, '/task3/found_garbage', self._callback, 10
        )
        self.status_pub = self.create_publisher(String, '/task3_judge/status', 10)

        self.get_logger().info('=' * 55)
        self.get_logger().info(' Task 3 Judge 起動完了 — 完全探索・分類チャレンジ')
        self.get_logger().info(' トピック: /task3/found_garbage (trail_kachaka_msgs/FoundGarbage)')
        self.get_logger().info(' 有効クラス: bottle / cup / can')
        self.get_logger().info(f' 画像保存先: {SAVE_DIR}')
        self.get_logger().info('=' * 55)

    def _callback(self, msg: FoundGarbage):
        if msg.garbage_class not in VALID_CLASSES:
            self.get_logger().warn(
                f'無効なクラス: "{msg.garbage_class}" — 有効値: {VALID_CLASSES}'
            )
            return

        n = len(self.received) + 1
        item = {
            'id': n,
            'class': msg.garbage_class,
            'confidence': round(float(msg.confidence), 3),
            'x': round(float(msg.robot_x), 2),
            'y': round(float(msg.robot_y), 2),
        }
        self.received.append(item)

        counts = {}
        for it in self.received:
            counts[it['class']] = counts.get(it['class'], 0) + 1

        self.get_logger().info(
            f'[受信 #{n}] class={item["class"]}  '
            f'conf={item["confidence"]:.1%}  '
            f'pos=({item["x"]:.1f}, {item["y"]:.1f})  '
            f'| 累計: bottle={counts.get("bottle",0)} '
            f'cup={counts.get("cup",0)} can={counts.get("can",0)}'
        )

        self._show_and_save_image(msg, n)
        self._publish_status(counts)

    def _show_and_save_image(self, msg: FoundGarbage, n: int):
        if not CV2_AVAILABLE or len(msg.image.data) == 0:
            return
        try:
            np_arr = np.frombuffer(bytes(msg.image.data), np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is None:
                return

            # ウィンドウに表示（手動で閉じるまで残る）
            win_title = f'Task3 Judge — #{n} {msg.garbage_class}'
            cv2.imshow(win_title, img)
            cv2.waitKey(1)

            # ファイルに保存
            timestamp = datetime.now().strftime('%H%M%S')
            filename = SAVE_DIR / f'{n:02d}_{msg.garbage_class}_{timestamp}.jpg'
            cv2.imwrite(str(filename), img)
            self.get_logger().info(f'  画像保存: {filename.name}')
        except Exception as e:
            self.get_logger().warn(f'画像処理エラー: {e}')

    def _publish_status(self, counts: dict):
        msg = String()
        msg.data = json.dumps(
            {
                'task': 3,
                'received': len(self.received),
                'by_class': counts,
                'items': self.received,
            },
            ensure_ascii=False,
        )
        self.status_pub.publish(msg)


def main():
    rclpy.init()
    node = Task3Judge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
