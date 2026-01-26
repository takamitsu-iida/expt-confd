#!/usr/bin/env python3

"""
ConfDステータス情報提供デーモン
このスクリプトはConfDのデータプロバイダとして動作し、
サーバーの稼働時間や最終チェック時刻などのステータス情報を提供します。
"""


import socket
import _confd
import _confd.dp as dp
import time
from datetime import datetime

# 起動時刻を記録
START_TIME = datetime.now()

def get_elem_callback(tctx, kp):
    """
    ConfDからのデータ要求(get_elem)に対する応答
    """
    path = str(kp)
    print(f"DEBUG: Received request for path: {path}")

    if "uptime" in path:
        delta = datetime.now() - START_TIME
        val = _confd.Value(str(delta).split('.')[0], _confd.C_STR)
    elif "last-checked-at" in path:
        now = datetime.now().strftime("%H:%M:%S")
        val = _confd.Value(now, _confd.C_STR)
    else:
        return _confd.ERR_NOT_FOUND

    # 値を返却
    dp.data_reply_value(tctx, val)
    return _confd.OK

def run():
    # 1. ソケットの作成と接続
    ctlsock = socket.socket()
    wrksock = socket.socket()
    dp.connect(ctlsock, dp.CONTROL_SOCKET, '127.0.0.1', 4565)
    dp.connect(wrksock, dp.WORKER_SOCKET, '127.0.0.1', 4565)

    # 2. デーモンの初期化
    dctx = dp.init_daemon("status_provider_daemon")

    # 3. コールバックの登録
    cbs = dp.DataCallbacks()
    cbs.get_elem = get_elem_callback
    # 第2引数はYANGの callpoint 名と一致させること
    dp.register_data_cb(dctx, "server_status_cp", cbs)
    dp.register_done(dctx)

    print("Status Provider is running... (Press Ctrl+C to stop)")

    try:
        while True:
            # ConfDからのリクエスト（Control Query）を待機
            # 内部的に select() が使われ、リクエストが来るまでブロックします
            dp.read_control_query(ctlsock, dctx)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        ctlsock.close()
        wrksock.close()

if __name__ == "__main__":
    run()