# kakeibo_automation

マネーフォワード家計簿が自動取得に対応していない決済サービスについて、一日一回スクレイピングにより取得、更新するためのコード。いまのところ楽天キャッシュに対応。

動作としては、実行した日の前日 1 日分の履歴を決済サービスから取得し、マネーフォワード家計簿に追加する。

## Quick Start

Ver 3.11 の Python 環境と Google Chrome を前提にしています。

### (ラズパイのみ) chromedriver のインストール

```
$ sudo apt install chromium-chromedriver
```

### リポジトリの clone

```
$ git clone https://github.com/thgcMtdh/kakeibo_automation.git
```

### .env ファイルの作成

```
$ cd kakeibo_automation
$ touch .env
```

以下の内容を記入する

```env
RAKUTEN_ID=""  # 楽天会員ID
RAKUTEN_PASS=""  # 楽天会員パスワード
MONEYFORWARD_ID=""  # マネーフォワード家計簿ID
MONEYFORWARD_PASS=""  # マネーフォワード家計簿パスワード
```

### Python 仮想環境作成

```
$ cd kakeibo_automation
$ python -V
Python 3.11.1  // 3.11系が動くことを確認

$ python -m venv venv  // 仮想環境作成
$ venv\Scripts\Activate.ps1  // 仮想環境有効化(Win)
$ source venv/bin/activate  // 仮想環境有効化(Mac)

$ python -m pip install -r requirements.txt  // ライブラリ一括インストール
```

### 実行

```
$ python copy_transactions_to_mf.py
```

## 構成ファイル

- copy_transactions_to_mf.py
  - とりあえず全部の関数をこのファイルにまとめることにした
