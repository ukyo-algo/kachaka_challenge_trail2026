# Kachaka Simulation Challenge — タスク仕様書

---

## 競技環境

### シミュレーション起動

```bash
ros2 launch kachaka_utils launch_sim.launch.py task:=<タスク番号>
```

`task:=1/2/3` を指定すると、タスクに対応したワールドと **自動採点ノード** が同時に起動します。

### 使用可能なトピック一覧

| トピック名 | 型 | 用途 |
|---|---|---|
| `/kachaka/front_camera/image_raw/compressed` | `sensor_msgs/CompressedImage` | 前面カメラ（推奨）|
| `/kachaka/back_camera/image_raw` | `sensor_msgs/Image` | 後面カメラ |
| `/kachaka/tof_camera/image_raw` | `sensor_msgs/Image` | ToF 深度画像 |
| `/kachaka/lidar/scan` | `sensor_msgs/LaserScan` | 2D LiDAR |
| `/kachaka/object_detection/result` | `kachaka_interfaces/ObjectDetectionListStamped` | YOLO 物体検出結果 |
| `/kachaka/manual_control/cmd_vel` | `geometry_msgs/Twist` | 速度指令（手動）|
| `/tf` | `tf2_msgs/TFMessage` | 自己位置（map→odom 変換）|
| `navigate_to_pose` | Nav2 Action | ナビゲーション指令 |

### 制約

- 音声・LLM は使用しない（シミュレーション環境では非対応）
- 物理的な棚の移動は不可

### 補足事項 

タスク2以降について、物体検出が必要となりますが、Gazeboの3Dモデルだと検出確率が低くなります。タスク2のcanは、正面を向けば信頼度は低くとも検出できることが多かったです。タスク3のbottle, cupについては未検出・誤検出となる確率が多くなるかもしれません。

---

## Task 1 — ウェイポイントナビゲーション

**難易度**: ★☆☆

### 概要

Nav2 を使って指定された 5 箇所のウェイポイントを順番に巡回する。

### ウェイポイント

```python
WAYPOINTS = [
    (5.0,  3.0),   # WP1: 棚エリア手前  （赤マーカー）
    (-3.0, 5.0),   # WP2: 倉庫中央      （緑マーカー）
    (8.0, -4.0),   # WP3: 奥エリア      （青マーカー）
    (-6.0,-2.0),   # WP4: 左エリア      （黄マーカー）
    (0.0,  0.0),   # WP5: スタート地点  （オレンジマーカー）
]
```

ワールド内に色付きの円柱マーカーが置かれているので、目視で確認できます。

### 採点

**採点は自動** です。ロボットが各ウェイポイントから **2.0m 以内** に入ると自動で記録されます。

```
スコア = 到達ウェイポイント数 × 20点
```

採点結果の確認:

```bash
ros2 topic echo /task1_judge/status
```

### 実装目標

- `NavManager.go_to(x, y)` を使って各座標へ移動するプログラムを書く
- 到達失敗時のリカバリー（次のウェイポイントへ進むなど）を実装する

---

## Task 2 — ゴミ検出チャレンジ　★メインタスク★

**難易度**: ★★☆　**推奨所要時間**: 3〜5 時間

### 概要

倉庫内に配置された **10 個の缶** を YOLO で検出し、発見した情報を採点ノードに送信する。

### ゴミの座標（公開情報）

ゴミは以下の座標付近に配置されています:

| # | x | y |
|---|---|---|
| 1 | 5.5 | 2.5 |
| 2 | 4.5 | 4.0 |
| 3 | -3.0 | 4.5 |
| 4 | -2.0 | 6.0 |
| 5 | 7.5 | -3.5 |
| 6 | 9.0 | -5.0 |
| 7 | -6.5 | -0.5 |
| 8 | -7.0 | -3.0 |
| 9 | 2.5 | 3.5 |
| 10 | -0.5 | 2.0 |

### 採点トピック

ゴミを発見したら、以下のトピックにメッセージを送信してください:

```
トピック名: /task2/found_garbage
メッセージ型: trail_kachaka_msgs/FoundGarbage
```

**FoundGarbage フィールド**:

```
std_msgs/Header header       # タイムスタンプ
string garbage_class         # "can"
float32 confidence           # YOLO の信頼度 (0.0〜1.0)
float32 robot_x              # 発見時のロボット X 座標
float32 robot_y              # 発見時のロボット Y 座標
sensor_msgs/CompressedImage image  # 検出画像（空でも可）
```

採点ノード（自動起動）が受信して結果を表示します:

```bash
ros2 topic echo /task2_judge/status
```

### 採点

```
スコア = 発見数 × 10点
（重複チェック: 2.0m 以内の再送は無視される）
```

### 実装目標

1. ゴミの座標を順番に巡回しながら YOLO で缶を検出する（クラス ID: 46）
2. 発見したら `FoundGarbage` を `/task2/found_garbage` に publish する

---

## Task 3 — 完全探索・分類チャレンジ

**難易度**: ★★★　

### 概要

倉庫全体を自律探索し、**3 種類のゴミ（計 10 個）** を発見・分類する。  
**ゴミの位置は非公開** — 自分で探索戦略を設計すること。

### ゴミの種類

| 種類 | YOLO クラス ID | Gazebo モデル |
|---|---|---|
| bottle | 39 | Beer |
| cup | 41 | Plastic Cup |
| can | 46 | Coke Can |

### 採点トピック

```
トピック名: /task3/found_garbage
メッセージ型: trail_kachaka_msgs/FoundGarbage
```

`garbage_class` に `"bottle"` / `"cup"` / `"can"` のいずれかを入れること。

```bash
ros2 topic echo /task3_judge/status
```

### 採点

```
スコア = 発見数 × 10点
```

### 実装目標

1. グリッド探索などで倉庫全体を網羅する探索戦略を設計する
2. YOLO で 3 種類のゴミを検出・分類する
3. 発見したら `FoundGarbage` を `/task3/found_garbage` に publish する

---

## Bonus Task — 深度測定精度チャレンジ

**難易度**: ★★★（任意参加）

ToF カメラを使ってゴミの 3D 位置（map 座標系）を推定し、以下のトピックに publish する:

```
トピック名: /task_bonus/found_items_3d
メッセージ型: std_msgs/String（JSON 形式）
フォーマット: {"id": 1, "x": 3.2, "y": -1.5, "z": 0.05}
```

---

## 学習ロードマップ

```
STEP 1: ROS2 基礎
    → ノード / トピック / rclpy.spin() を理解する

STEP 2: Task 1 (ナビゲーション)
    → NavManager で go_to() を使ってロボットを動かす

STEP 3: Task 2 前半 (カメラ処理)
    → CompressedImage を cv2 に変換する
    → YOLO で物体を検出し /task2/found_garbage に送信する

STEP 4: Task 2 後半 (状態機械)
    → 状態（移動中 / 探索中 / 発見済み）を設計する
    → 非同期コールバックを組み合わせる

STEP 5: Task 3 (自律探索)
    → グリッド探索パターンを実装する
    → 3 クラス分類を組み込む

STEP 6: Bonus (3D 認識)
    → ToF カメラで深度を取得する
    → tf2 で map 座標系に変換する
```
