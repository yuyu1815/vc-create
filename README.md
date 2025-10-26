# vc-create — Discord VC自動作成ボット

このリポジトリは、Discordサーバーで「ベースVC」に誰かが入室すると、その設定を丸ごとコピーした専用ボイスチャンネル（VC）を自動生成し、ユーザーを自動移動させるボットの実装です。無人になった自動生成VCは一定時間後に自動削除されます。ギルド既定設定に加えて、各ベースVCごとの個別テンプレートも管理できます。

主な用途例:
- 雑談/作業部屋を必要に応じて自動で増やしたい
- 一人一部屋のVCを作り、メンバーごとに分離したい
- VCの乱立を避けつつ、使われた部屋だけ自動で用意・後片付けしたい

---

## 特徴
- /vc create で「ベースVC」を作成
- 入室トリガーでベースVCの設定を完全コピーして新VCを生成
  - 名前/カテゴリ/ビットレート/ユーザー上限/NSFW/パーミッションオーバーライド の複製
  - 同時入室も安全に処理（ユーザーごとに個別VCを作成）
- 無人になった自動生成VCは設定秒数後に自動削除
- 名前テンプレートに `{user_name}` と `{count}`（ギルドごとの連番）を使用可能
- 生成上限、削除遅延、ログ出力先チャンネルなどを設定可能
- スラッシュコマンド中心（ハイブリッド対応）
- SQLite データベースで状態を永続化
- Docker サポート

---

## 目次
- 準備（必要要件・権限）
- クイックスタート（ローカル / Docker）
- コマンド一覧
- 設定と動作の詳細
- データベーススキーマ
- トラブルシューティング
- 開発（構成・貢献）
- ライセンスと謝辞

---

## 準備

### 必要要件
- Python 3.12 以降（`requirements.txt` のライブラリを使用）
- Discord Bot トークン
- 適切な Bot 権限（VC作成/移動/権限編集 など）

### 必要なDiscord権限（推奨）
- チャンネルを管理（Manage Channels）
- メンバーを移動（Move Members）
- 権限を管理（Manage Roles）
- ボイスチャンネル接続/発言

招待URLの例:
```
https://discord.com/oauth2/authorize?client_id=YOUR_APP_ID&scope=bot%20applications.commands&permissions=PERMISSIONS
```
- `YOUR_APP_ID` をアプリケーションIDに置き換えてください。
- `PERMISSIONS` は上記権限を満たす値に設定してください（Discord開発者ポータルで確認可能）。

### 環境変数
本プロジェクトは `python-dotenv` による `.env` 読み込みをサポートしています。最低限、以下を設定してください。

- `TOKEN` — Discord Bot トークン

Windows の場合（PowerShell）:
```
setx TOKEN "YOUR_BOT_TOKEN"
```
または、プロジェクト直下に `.env` を作成して記述します。

---

## クイックスタート

### ローカル実行
1) 依存関係のインストール
```
python -m pip install -r requirements.txt
```
2) Bot を起動
```
python bot.py
```
- 環境により `py` / `python3` などに置き換えてください。

起動後、オーナーはコマンド同期を行えます（下記「オーナー専用コマンド」を参照）。

### Docker
Docker と Docker Compose が使用できます。
```
docker compose up -d --build
```
- `-d` はバックグラウンド実行です。

---

## コマンド一覧

### VC 管理（スラッシュ）
- `/vc help` — VC 機能の使い方を表示（現在設定のサマリ付き）
- `/vc create [チャンネル名?]` — ベースVCを作成
- `/vc setting channel_name <ベースVC> <テンプレート>`
  - 各ベースVCに個別の名前テンプレートを設定（使用可能トークン: `{user_name}`, `{count}`）
- `/vc setting max_channels <数値>` — 自動生成VCの同時上限（既定: 50）
- `/vc setting delete_delay <秒>` — 無人後に削除するまでの秒数（既定: 30）
- `/vc log_channel <チャンネル>` — ログ出力先テキストチャンネルを設定（任意）

### 一般（ハイブリッド）
- `help` — ボットが読み込んだ全コマンドを一覧表示
- `botinfo` — ボット情報
- `serverinfo` — サーバー情報
- `ping` — 生存/遅延確認

### オーナー専用
- `sync <global|guild>` — スラッシュコマンドを同期
- `unsync <global|guild>` — スラッシュコマンドの同期解除
- `unload <cog>` — Cog をアンロード
- `reload <cog>` — Cog をリロード

---

## 設定と動作の詳細

### 名前テンプレート
- ギルド既定テンプレート（`guild_vc_settings.base_name_template`）
- ベースVC個別テンプレート（`vc_base_channels.name_template`）
- 生成時は「ベースVC個別」→「ギルド既定」の優先で採用されます。
- 利用可能トークン
  - `{user_name}` — 生成をトリガーしたユーザーの表示名
  - `{count}` — ギルドごとの通し番号（`name_counter` をインクリメント）

### 自動削除
- Bot が生成した VC のみが対象
- 無人になってから `delete_delay` 秒後に削除
- 進行中タスクはチャンネルごとに管理し、重複削除を防止

### 生成上限
- `max_channels` で同時に存在できる自動生成 VC 数を制限

### ログ
- `/vc log_channel` で設定したチャンネルにイベントログを送信可能

---

## データベース
- SQLite を使用（`database/database.db`）
- 初期スキーマは `database/schema.sql` に定義

主なテーブル:
- `guild_vc_settings`
  - `base_name_template` / `name_counter` / `max_channels` / `delete_delay` / `log_channel_id`
- `vc_base_channels`
  - `/vc create` で作られたベースVCの記録と個別テンプレート
- `vc_generated_channels`
  - Bot が生成した複製 VC の作成・削除時刻など

---

## トラブルシューティング
- スラッシュコマンドが表示されない
  - オーナーが `sync global` または `sync guild` を実行してください
  - グローバル同期は反映に数分～1時間ほどかかることがあります
- チャンネル作成に失敗する / 403 になる
  - Bot の権限（チャンネル管理/移動/権限編集）を確認
  - カテゴリや役職の権限上書きに阻害されていないか確認
- ユーザーが自動で移動しない
  - ボイスチャンネルの接続/発言/メンバー移動の権限を確認
- 起動しない / トークンエラー
  - `TOKEN` 環境変数（または `.env`）が正しく設定されているか確認

---

## 開発

### プロジェクト構成（抜粋）
- `bot.py` — 起動、ロガー、Cog ロード、イベントハンドラ
- `cogs/voice.py` — VC 自動作成/コピー/自動移動/自動削除の中核
- `cogs/general.py` — 一般コマンド
- `cogs/owner.py` — オーナーコマンド（同期/アンロード/リロード）
- `database/` — DB 本体と初期スキーマ
- `requirements.txt` — 依存関係
- `docker-compose.yml`, `Dockerfile` — コンテナ実行

### コントリビューション
- バグ報告・改善案は Issue / PR を歓迎します
- ルールは `CONTRIBUTING.md` と `CODE_OF_CONDUCT.md` を参照

---

## ライセンスと謝辞
- 本プロジェクトは Apache License 2.0 の下で提供されます。詳細は `LICENSE.md` を参照してください。
- 一部の実装や構成は [kkrypt0nn/Python-Discord-Bot-Template](https://github.com/kkrypt0nn/Python-Discord-Bot-Template) に着想を得ています。ありがとうございます。

---

## 変更履歴
更新内容は `UPDATES.md` を参照してください。
