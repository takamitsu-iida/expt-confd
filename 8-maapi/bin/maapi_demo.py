#!/usr/bin/env python3
"""Simple MAAPI example (Python)

このスクリプトは ConfD の MAAPI を Python から直接呼び出す最小構成の例です。

YANG モジュール (yang/example.yang):

- container demo
  - leaf message (string)
  - leaf last-updated (string)

動き:
- ConfD に MAAPI で接続し、running データストア上の /demo 以下を操作
- demo コンテナが存在しない場合は作成し、初期値を書き込む
- 既存の message / last-updated を読み出して表示
- last-updated を現在時刻で更新してコミット

使い方:
- このディレクトリで `make init && make all && make start` を実行して ConfD を起動
- 別シェルで `python bin/maapi_demo.py` を実行
- `confd_cli` から `show running-config demo` などで値を確認できます。
"""

import socket
import sys
from datetime import datetime

try:
    import _confd  # type: ignore
    import _confd.maapi as maapi  # type: ignore
except ImportError as e:  # pragma: no cover - 実行環境依存
    print(f"Error: Could not import ConfD Python modules: {e}")
    print("Make sure ConfD is installed and PYTHONPATH is set correctly.")
    sys.exit(1)

CONFD_HOST = "127.0.0.1"
CONFD_PORT = _confd.CONFD_PORT

# この例では module 名は "example" だが、MAAPI のパス文字列では
# モジュールプレフィックスを付けずに "/demo/..." だけを使う。
DEMO_PATH = "/demo"
MESSAGE_PATH = "/demo/message"
LAST_UPDATED_PATH = "/demo/last-updated"


def connect_maapi() -> socket.socket:
    """MAAPI ソケットに接続し、スキーマを読み込んで返す"""
    sock = socket.socket()
    # maapi_example.py と同様のスタイルで接続
    maapi.connect(sock=sock, ip=CONFD_HOST, port=CONFD_PORT)
    maapi.load_schemas(sock)
    return sock


def start_rw_trans(sock: socket.socket) -> int:
    """running データストアに対する READ_WRITE トランザクションを開始"""
    user = "admin"
    groups = ["admin"]
    context = "maapi-demo"

    # ユーザセッション開始
    maapi.start_user_session(
        sock,
        user,
        context,
        groups,
        CONFD_HOST,
        _confd.PROTO_TCP,
    )

    # running に対する書き込み可能トランザクションを開始
    th = maapi.start_trans(sock, _confd.RUNNING, _confd.READ_WRITE)
    return th


def ensure_demo_exists(sock: socket.socket, th: int) -> None:
    """/demo が存在しなければ作成し、初期値を書き込む"""

    if not maapi.exists(sock, th, DEMO_PATH):
        # コンテナ demo を作成
        maapi.create(sock, th, DEMO_PATH)
        # 初期メッセージとタイムスタンプを書き込み
        maapi.set_elem(sock, th, "Hello from MAAPI!", MESSAGE_PATH)
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        maapi.set_elem(sock, th, now, LAST_UPDATED_PATH)


def read_demo(sock: socket.socket, th: int) -> tuple[str, str]:
    """/demo/message と /demo/last-updated を読み出す"""
    msg = ""
    ts = ""

    if maapi.exists(sock, th, MESSAGE_PATH):
        msg = str(maapi.get_elem(sock, th, MESSAGE_PATH))
    if maapi.exists(sock, th, LAST_UPDATED_PATH):
        ts = str(maapi.get_elem(sock, th, LAST_UPDATED_PATH))

    return msg, ts


def update_last_updated(sock: socket.socket, th: int) -> str:
    """last-updated を現在時刻で更新し、その値を返す"""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    maapi.set_elem(sock, th, now, LAST_UPDATED_PATH)
    return now


def main() -> int:
    sock = connect_maapi()
    try:
        th = start_rw_trans(sock)

        # /demo が無ければ作成して初期値投入
        ensure_demo_exists(sock, th)

        # 現在値を読み出し
        msg, ts = read_demo(sock, th)
        print("[before]")
        print(f"  message      : {msg}")
        print(f"  last-updated : {ts}")

        # last-updated を更新
        new_ts = update_last_updated(sock, th)

        # 変更を適用
        maapi.apply_trans(sock, th, False)
        maapi.finish_trans(sock, th)

        print("[after]")
        print(f"  message      : {msg}")
        print(f"  last-updated : {new_ts}")

    finally:
        try:
            # セッションを明示的に終了 (失敗しても致命的ではない)
            try:
                maapi.end_user_session(sock)
            except Exception:
                pass
        finally:
            sock.close()

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
