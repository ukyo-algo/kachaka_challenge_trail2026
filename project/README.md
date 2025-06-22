# 補足資料
## cloneした後は、、、？
- まず初めに仮想環境(コンテナ)を立てる。
    - 初めにイメージ(設計図みたいなもの)を作成して、その後コンテナ(実際の家)を作成する。
    - イメージの作成には結構な時間(10分弱)掛かると思われるので、気長に待とう
```bash
# ~/trail/kachaka_challenge_trail2025
make build-app

./run-docker-container.py [自分の名前] # 例: ./run-docker-container.py takeuchi
```

```bash
# if you use a real kachaka for development
./run-docker-container.py [自分の名前] -r
```

- その後、コマンドパレットから```Attach to Running Container...```を検索して、クリック
    - [自分の名前]_sim_kachaka_project_1(e.g. takeuchi_sim_kachaka_project_1)を選ぶ

- その後、少しすると新しい画面に切り替わるので、そこで自分のさっきの作業フォルダを開く。その際、(Ctrl + K) > (Ctrl + O)を教えて開くフォルダの選択を行い、```/app```を選択すればいい。

- 画面が切り替わって、自分の先居たような作業フォルダが開かれれば大丈夫である。

## Initial Setup
- 初回開くときは、バージョン管理uvソフトのsetupとプロジェクトのビルドが必要である。
### uvの初期化
```
# /app/
uv venv # 仮想環境の中で仮想環境を立ち上げる
uv sync # pyproject.tomlの中に入っているパッケージ一覧を全てダウンロード(synchronize)
```

### projectのビルド
```
# /app/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

## とりあえずsim環境を動かしてみる
```bash
ros2 launch kachaka_utils launch_sim.launch.py
```

以下のコマンドで、kachaka をキーボードで動かすことができるようになる

```bash
# コンテナ内の別のターミナルで動かす
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap cmd_vel:=/kachaka/manual_control/cmd_vel
```

## terminatorの使い方
ROSを動かすときはターミナルが複数同時に必要な場合が多い。その際、一つの画面に一杯別のターミナルを立ち上げることのできるソフトウェア(terminal multiplexer)が必要となる。このコンテナにはそのソフトウェアとしてterminatorがインストールされているので、それを使ってもらいたい。

vscodeのターミナルで
```
terminator
```
と打つと黒の新しい画面が出てくると思う

- ```Ctrl + Shift + E```で垂直に新しい画面を作る
- ```Ctrl + Shift + O```で水平に新しい画面を作る

## 初めてのpackageを作ってみよう！
注: 言語はpythonでのものを解説します。公式チュートリアルと一部違います。これは公式が生のpython, pipを使っているのに対して、このコンテナではuv環境を使っているからです。(あまり深追いしなくてもいいが、docker環境中の生のpipは~~適切に管理しないと、すぐバージョン問題で動かなくなるぐらい本当にカス~~なので、poetryやuvを使用しよう)

### packageとは？
packageとは、ある機能を果たすプログラム群をまとめたものとして解釈できる。numpyは行列計算等に特化したpackageであり、matplotlibはグラフ描画に特化したpackageである。これは自分たちの作るプログラムもそうで、プログラムが段々大きくなっていくと、プログラムをパッケージごとに整理する必要がある。

ROSでも機能ごとにpackageに分ける必要がある。分け方は以下のような例が考えられる。
```
ros2_ws/src/
　├ kachaka_img/              ## 画像処理(物体検知等)を担当するpackage, node群です。
　├ kachaka_nav/              ## navigationを担当するpackage, node群です。
　├ kachaka_human_tracking/   ## 人間を追いかける処理を担当するpackage, node群です。
　├ trail_mpc_task_manager/   ## 実際のタスクのエントリーポイントとなるpackage, node群です。
　├ kachaka_ros2_dev_kit/     ## kachakaを最低限動かすために必要なpackage, node群です。
　└ kachaka_utils/            ## その他の基本的機能を実装するために必要なpackage, node群です。
```

ROSにおいてはpackageの中に、それぞれの機能が入ったnodeが複数入っている。nodeは基本的には一つずつsrc/kachaka_utilsの中のファイルの中に入っており、classとして定義されている。一方で、これらnodeを動かすときにはscripts/executor.pyにおいて、実際に動かす処理を行う。自分でpackage, nodeを新しく組むときは、trail_kachaka_exampleを参考にしてみよう。

ちなみに以下に書かれている話は少し難しいかもしれないので、分からない人はexampleコードを真似するので大丈夫！！

ROSにおいては、packageの中に、それぞれの機能が入ったnodeが複数入っている。nodeのように非常に独立性の高いものではなくても、機能をまとめたcomponentとも言えるものは作成可能である。

つまり、今回のタスクに対して、task_manager_pkgというpackageを作成したとして、task_manager_pkgの中に作るnode、そしてcomponent、他パッケージに作るnode、(そしてcomponentだが、あまり良い設計ではないので今回は省く)の3(4)通りの作成方法が可能である。

使い分けとしては、
+ 組み入れる処理は一般性の高い処理ですか？(画像認識等; 今回のタスクがなくても、その処理は必要な場合が多分にありますか？)
    - **Yes**: 他パッケージに作るnode
    - **No**: 同じパッケージの中に入れ込む
        + 組み入れる処理は繰り返しが多く、また処理の時間軸が異なる方がよいことがありますか？
            - **Yes**: 同じパッケージに作るnode
            - **No**: 同じパッケージに作るcomponent

とはいえ、これは大体の使い分けであるし、バランスというのもあるから(少々難しい話かもしれないが、例えばcomponentばかり作ってしまうと、一つのスレッドに過負荷を与えざるをえない処理体系を作ることとなり、パフォーマンスを落とすことになることも稀にある)ある程度は考えて作らないといけない。

この塩梅だったり、使い分けだったりは書いてる人(takeuchi(3))ですら答えは全く出ていない話なので、皆も試行錯誤しつつ、頑張ってみてもらいたい。

### packageを作成する
**このレポジトリにおいてのみ**下の方法でpackageを作成することができる。
```
# ros2_ws/src
create_ros2_pkg
```
packageの名前、その他作成者の属性が聞かれると思うので、入力すればよい。

<details><summary>(参考)この裏ではどのような処理が行われているのか？</summary>

cookiecutterというtemplateからプログラムを作成してくれるソフトを用いています。

```
alias create_ros2_pkg="cookiecutter ../../template/"
```

という処理をして、エイリアス(別名; ```create_ros2_pkg```)を```cookiecutter ../../template/```という処理に付けています
</details>

### nodeの立ち上げ方
プログラムを書き上げたら、ROSがプログラムを実行できるように実行権限を変えるために、```chmod +x [programのパス]```をする。プログラムを書き上げたら、先ほどと同じように```colcon build --symlink-install```としてビルドを行う。
```
# /app/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

その後terminatorを立ち上げて、一つ目の画面で以下
```
ros2 launch kachaka_utils launch_sim.launch.py
```

その後、```ctrl + shift + e```又は```ctrl + shift + o```で二つ目の画面を立ち上げ、そこで以下
```
ros2 run [自分で作成したパッケージ名] [その中で、scripts以下のところで実行するファイル]
ros2 run [自分の作成したパッケージ名] executor.py
```

ちなみに、tab補完といって例えば自分の作成したパッケージ名のところで何が実行できるか分からないときはtabを二回押せば、何があるかどうかを一覧で見ることができる。

### launchファイルの立ち上げ方
launchファイルはnodeをまとめて立ち上げる際に極めて有用である。launchファイルの作り方は以下の記事を参照すること。

### CMakelists.txtの書き方
CMakelists.txt, package.xmlはどのようにビルドを行うかの設定が書かれたファイルである。少し発展的だが、packageを作成するときには時折必要となる。書き方は以下の記事などを参照すること。

## kachakaから出るtopic名一覧
[この記事の](https://github.com/CyberAgentAILab/kachaka_ros2_dev_kit/blob/jazzy/kachaka_gazebo/README.md)サポートマトリクスというところにトピック一覧が載っているのでそこを参照するとよい。その際、右に丸バツが掛かれているが、これは物理シミュレーションがそのトピックを吐き出しているか(物理シミュレーションも完全ではなく、限界があるので、一部トピックは出すのが非常に難しいからである)を示しているものであり、実機においては何の問題もなく使用することができるので、そこを留意せよ。

## Navigationについて
所謂足回りの話である。今回は開発の短さなどを鑑みて、ナビゲーションを行う関数についてはこちら側で既存のものを提供する。(navigator.py)となっている。勿論このnavigator.pyに限界などを感じた場合には新規で作成しても全く構わない。基本的には[Nav2](https://docs.nav2.org/)のラッパーである。使い方は以下となっている

{工事中}

## マップ作成・spottingについて
ルールブックによれば、事前にフィールドのマップを作成する時間が与えられ、またフィールド上のいくつかの地点についてはそのおおよその座標を取ることが可能である。TRAILでは前者の作業を**マップ作成**といい、後者の作業を**spotting**という。マップ作成については、事前にそれ用のlaunchファイルを用意するので、それを用いてもらえばよい。spottingについては各々のチームが目的に合ったツールを作成することを期待する。


## 参考
- [公式チュートリアル](https://docs.ros.org/en/jazzy/index.html#)
    - 英語だけど一番わかりやすい
    - チュートリアルを進める際はdevcontainerでまっさらな環境を作って勉強したほうが分かりやすいかも
        - vscodeのコマンドパレットで```add devcontainer configuration files```と調べて、選択
            - ```ros```等で調べると色々出てくると思うので、一番上を選択
            - ROS distroはjazzyを選択
            - それ以外はdefaultを選択
                - 確かpython環境は入ってなかったので、devcontainerを立ち上げた後にpythonをインストールする必要がある。
- TRAIL Tutorial
    - ROS1だが、日本語資料として一応見てもらえたら、、、
