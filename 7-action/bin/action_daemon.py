#!/usr/bin/env python3
"""Simple ConfD action example (Python)

このスクリプトは ConfD の tailf:action を Python で実装する最小構成の例です。

YANG モジュール (yang/example.yang):

- container tools
  - tailf:action hello
    - tailf:actionpoint hello-python
    - input:  leaf name (string)
    - output: leaf greeting (string)

動き:
- ConfD から actionpoint "hello-python" に対してコールバックが呼ばれる
- 入力パラメータ name を受け取り、"Hello, <name>!" というメッセージを返す

使い方:
- このディレクトリで `make init && make all && make start` を実行して ConfD とこのデーモンを起動
- ConfD CLI(Jスタイル) で:

    config
    tools hello name <your-name>

  と打つと、greeting に Python で生成した文字列が返ってきます。
"""

import select
import signal
import socket
import sys
from typing import List

try:
    import _confd  # type: ignore
    import _confd.dp as dp  # type: ignore
    import _confd.error as confd_error  # type: ignore
except ImportError as e:  # pragma: no cover - 実行環境依存
    print(f"Error: Could not import ConfD Python modules: {e}")
    sys.exit(1)

try:
    # Makefile の confdc --emit-python で生成される
    from example_ns import ns  # type: ignore
except ImportError as e:  # pragma: no cover
    print("Error: example_ns.py が見つかりません。先に 'make all' を実行してください。")
    print(e)
    sys.exit(1)

CONFD_HOST = "127.0.0.1"
CONFD_PORT = _confd.CONFD_PORT
DAEMON_NAME = "simple_python_action_daemon"
ACTIONPOINT_NAME = "hello-python"  # YANG の tailf:actionpoint と一致させる


class HelloActionCallbacks:
    """`tools hello` アクションのコールバック実装

    - cb_init: ConfD から最初に呼ばれ、どの worker ソケットを使うか教える
    - cb_action: 実際のアクション本体。入力パラメータを受け取り、出力を返す
    - cb_abort: 長時間動作中のアクションがキャンセルされたときに呼ばれる
    """

    def __init__(self, worker_sock: socket.socket) -> None:
        self._worker_sock = worker_sock

    # ユーザアクションの初期化
    def cb_init(self, uinfo) -> int:  # type: ignore[override]
        dp.action_set_fd(uinfo, self._worker_sock)
        return _confd.CONFD_OK

    # アクション本体
    def cb_action(self, uinfo, name, keypath, params) -> int:  # type: ignore[override]
        # params[0] が input/name に対応する
        if params:
            who = str(params[0].v)
        else:
            who = "world"

        greeting = f"Hello, {who}! (from Python action)"

        # 出力 leaf greeting を 1 つだけ返す
        result: List[_confd.TagValue] = [
            _confd.TagValue(
                _confd.XmlTag(ns.hash, ns.example_greeting),
                _confd.Value(greeting, _confd.C_STR),
            )
        ]
        dp.action_reply_values(uinfo, result)
        return _confd.CONFD_OK

    # アクションがキャンセルされた場合
    def cb_abort(self, uinfo) -> None:  # type: ignore[override]
        dp.action_delayed_reply_error(uinfo, "aborted")


def main() -> int:
    """ConfD に接続して action コールバックを登録し、イベントループを回す"""

    # デーモンコンテキストとソケット準備
    dctx = dp.init_daemon(DAEMON_NAME)
    ctlsock = socket.socket()
    workersock = socket.socket()

    try:
        # ConfD に接続
        dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, CONFD_HOST, CONFD_PORT, None)
        dp.connect(dctx, workersock, dp.WORKER_SOCKET, CONFD_HOST, CONFD_PORT, None)

        # アクションコールバック登録
        acb = HelloActionCallbacks(workersock)
        dp.register_action_cbs(dctx, ACTIONPOINT_NAME, acb)
        dp.register_done(dctx)

        print("============================================================")
        print("Python action daemon is running.")
        print("Try in ConfD CLI (J style):")
        print("  config")
        print("  tools hello name <your-name>")
        print("============================================================")

        stop = False

        def _signal_handler(signum, frame):  # type: ignore[override]
            nonlocal stop
            stop = True

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        # select() で CONTROL / WORKER ソケットのイベントを待つ
        sockets = [ctlsock, workersock]
        while not stop:
            readable, _, _ = select.select(sockets, [], [], 1.0)
            for s in readable:
                try:
                    dp.fd_ready(dctx, s)
                except confd_error.Error as e:  # pragma: no cover
                    # ユーザコールバック内の例外など
                    if e.confd_errno is _confd.ERR_EXTERNAL:
                        print(f"Callback error: {e}")
                    else:
                        raise

    finally:
        try:
            workersock.close()
        finally:
            ctlsock.close()
            dp.release_daemon(dctx)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
