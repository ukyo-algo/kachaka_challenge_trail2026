# 実装ガイド — はじめての Kachaka 開発

---

## 1. パッケージの作り方

### パッケージとは？

ROS2 では、機能をパッケージという単位で整理します。今回は **タスクごとにパッケージを 1 つ作る** のが基本方針です。

```
ros2_ws/src/
├── my_task1/             # Task 1 用パッケージ
├── my_task2/             # Task 2 用パッケージ
├── kachaka_utils/        # タスク間で共通して使う機能（NavManager など）
└── trail_kachaka_sample/ # サンプルパッケージ（参考にしてください）
```

**タスク間で共通して使いまわしたいもの**（物体検出クラスなど）は `kachaka_utils/src/kachaka_utils/` に置くと、どのパッケージからでも `from kachaka_utils.xxx import Xxx` とインポートできます。

### パッケージを作成する

```bash
# /app/ros2_ws/src/
create_ros2_pkg
```

パッケージ名（例: `my_task2`）と作成者情報を入力するとテンプレートから自動生成されます。(coockiecutterを使用しています)

生成されるディレクトリ構成:

```
my_task2/
├── CMakeLists.txt         # ビルド設定
├── package.xml            # パッケージ情報・依存関係
├── launch/
│   └── task2.launch.py    # 複数ノードをまとめて起動したい場合に使う
├── src/
│   └── my_task2/          # Python モジュール（タスク固有のノードのクラス定義）
│       ├── __init__.py
│       ├── garbage_detector.py  # 検出ロジックのクラス
│       └── nav_strategy.py      # 探索戦略のクラス
└── scripts/
    └── executor.py        # エントリーポイント（ノードを起動する）
```

**ノードをどこに置くか**:

| 置き場所 | 使いどころ |
|---|---|
| `src/my_task2/` | そのタスク固有の処理（このパッケージの中だけで使う）|
| `kachaka_utils/src/kachaka_utils/` | 複数タスクで共通して使う処理（NavManager、汎用Detectorなど）|

**複数ノードを同時に起動したい場合**: `launch/` にlaunchファイルを置き、`ros2 launch my_task2 task2.launch.py` で一括起動できます。

`trail_kachaka_sample` パッケージが動く例になっているので参考にしてください。必要に応じて、package.xmlやlaunchファイルもテンプレートからコピーした状態から編集してください。

---

## 2. ノードの書き方

### 最小構成のノード

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class MyNode(Node):
    def __init__(self):
        super().__init__('my_node_name')
        self.get_logger().info('ノードが起動しました')

def main():
    rclpy.init()
    node = MyNode()
    rclpy.spin(node)    # ノードをイベントループで動かす
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### トピックを受信する（Subscriber）

```python
from sensor_msgs.msg import CompressedImage
from rclpy.qos import QoSProfile, ReliabilityPolicy

class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=1)
        self.create_subscription(
            CompressedImage,
            '/kachaka/front_camera/image_raw/compressed',
            self._image_callback,
            qos,
        )

    def _image_callback(self, msg):
        self.get_logger().info(f'画像受信: {len(msg.data)} bytes')
```

> カメラトピックは QoS に `BEST_EFFORT` を指定しないと受信できません。

### トピックを送信する（Publisher）

```python
from trail_kachaka_msgs.msg import FoundGarbage
from std_msgs.msg import Header

class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')
        self.pub = self.create_publisher(FoundGarbage, '/task2/found_garbage', 10)

    def publish_finding(self, x, y, confidence):
        msg = FoundGarbage()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.garbage_class = 'bottle'
        msg.confidence = confidence
        msg.robot_x = x
        msg.robot_y = y
        # msg.image = ...  # 画像を添付する場合
        self.pub.publish(msg)
```

---

## 3. NavManager でナビゲーションする

`kachaka_utils.nav_manager.NavManager` を使うと、Nav2 の詳細を知らなくても簡単にナビゲーションができます。

```python
from kachaka_utils.nav_manager import NavManager

class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')
        self.nav = NavManager(self)

    def run(self):
        # Nav2 が起動するまで待つ（必須）
        self.nav.wait_until_nav2_active()

        # 指定座標へ移動（到達まで待機）
        success = self.nav.go_to(x=5.0, y=3.0)

        if success:
            self.get_logger().info('到達成功！')
        else:
            self.get_logger().warn('到達失敗。')
```

**NavManager の主要メソッド**:

| メソッド | 説明 | 戻り値 |
|---|---|---|
| `wait_until_nav2_active()` | Nav2 が起動するまで待機（必ず最初に呼ぶ）| なし |
| `go_to(x, y, yaw=0.0)` | 指定座標へ移動（完了まで待機）| `bool` |
| `get_current_pose_stamped()` | 現在の自己位置を取得 | `PoseStamped` |
| `cancel_nav()` | 現在のナビゲーションをキャンセル | なし |

---

## 4. ノードのビルドと実行

### ビルド

```bash
# /app/ros2_ws/
colcon build --symlink-install
source install/setup.bash
```

### シミュレーション起動（別ターミナル）

```bash
ros2 launch kachaka_utils launch_sim.launch.py task:=1
```

### ノードの実行

```bash
ros2 run <パッケージ名> executor.py
```

`--symlink-install` を使っている場合、Python ファイルを編集後にリビルドなしで即座に反映されます（ただし CMakeLists.txt を変えた場合はビルドが必要）。

---

## 5. Task 2 の実装ヒント

### 全体の流れ

```
[起動] → [Nav2 待機] → [探索ポイントへ移動]
                              ↓
                        [カメラ画像取得]
                              ↓
                        [YOLO で検出]
                              ↓
                        [ゴミ発見？]
                          YES → /task2/found_garbage に publish
                          NO  → 次の探索ポイントへ
```

### カメラ画像を OpenCV で使う

```python
import numpy as np
import cv2

def _image_callback(self, msg):
    # CompressedImage → numpy 配列 → cv2 画像
    np_arr = np.frombuffer(bytes(msg.data), np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    # image を YOLO に渡す
```

### YOLO で検出する

YOLO モデルは `/app/yolo11n.pt` にあります。

```python
from ultralytics import YOLO

model = YOLO('/app/yolo11n.pt')
results = model(image)
for box in results[0].boxes:
    class_id = int(box.cls[0])
    confidence = float(box.conf[0])
    # class_id == 39 が bottle
```

### 重複チェック

同じゴミを何度も報告しないよう、発見済みリストと距離比較を行います:

```python
import math

found_items = []  # 発見済みの (x, y) リスト

def is_duplicate(robot_x, robot_y, threshold=2.0):
    for fx, fy in found_items:
        if math.sqrt((fx - robot_x)**2 + (fy - robot_y)**2) < threshold:
            return True
    return False
```

---

## 6. よくあるつまずきポイント

**Q. `go_to()` を呼んでもロボットが動かない**  
A. `wait_until_nav2_active()` を先に呼んでいるか確認。Nav2 の起動に 1〜2 分かかることがある。

**Q. カメラトピックを subscribe しても受信できない**  
A. QoS に `ReliabilityPolicy.BEST_EFFORT` を指定しているか確認。

**Q. トピックに何が来ているか確認したい**  
A. `ros2 topic echo <トピック名> --once` で 1 件受信して確認できる。

**Q. カメラ画像を画面に表示したい**  
A. `ros2 run rqt_image_view rqt_image_view` を起動してトピックを選択。

**Q. ビルドしたのに変更が反映されない**  
A. `source install/setup.bash` を再実行しているか確認。`--symlink-install` 付きでビルドしていれば Python ファイルは再ビルド不要。

**Q. `/task2/found_garbage` を publish しても採点ノードに届かない**  
A. `ros2 topic list` で `/task2/found_garbage` が表示されているか確認。シミュレーションを `task:=2` で起動しているか確認。

---

## 7. 参考リンク

- [ROS2 Jazzy 公式チュートリアル](https://docs.ros.org/en/jazzy/Tutorials.html)
- [Nav2 ドキュメント](https://docs.nav2.org/)
- [YOLO（Ultralytics）ドキュメント](https://docs.ultralytics.com/)
- [Kachaka トピック一覧](https://github.com/CyberAgentAILab/kachaka_ros2_dev_kit/blob/jazzy/kachaka_gazebo/README.md)
