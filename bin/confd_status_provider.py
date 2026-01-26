#!/usr/bin/env python3

import socket
import _confd
import _confd.dp as dp
import time
from datetime import datetime

# 起動時刻を記録
START_TIME = datetime.now()

def get_elem_callback(tctx, kp):
    # (既存のコールバック内容は変更なし)
    path = str(kp)
    if "uptime" in path:
        delta = datetime.now() - START_TIME
        val = _confd.Value(str(delta).split('.')[0], _confd.C_STR)
    elif "last-checked-at" in path:
        now = datetime.now().strftime("%H:%M:%S")
        val = _confd.Value(now, _confd.C_STR)
    else:
        return _confd.ERR_NOT_FOUND
    dp.data_reply_value(tctx, val)
    return _confd.OK

def run():
    # 1. Daemon Context を作成
    dctx = dp.init_daemon("status_provider_daemon")

    ctlsock = socket.socket()
    wrksock = socket.socket()

    # 先ほど成功した接続シグネチャを使用
    # (環境によって None が不要な場合は適宜調整してください)
    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
    dp.connect(dctx, wrksock, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)
    print("Connected successfully!")

    # 2. 【修正】コールバックを辞書として定義
    # クラスではなく、単なる dict に関数を紐付けます
    cbs = {
        'get_elem': get_elem_callback
    }

    # 3. 登録
    dp.register_data_cb(dctx, "server_status_cp", cbs)
    dp.register_done(dctx)

    print("Status Provider is running... (Wait for 'show server-status')")

    try:
        while True:
            dp.read_control_query(ctlsock, dctx)
    except KeyboardInterrupt:
        pass
    finally:
        ctlsock.close()
        wrksock.close()

if __name__ == "__main__":
    run()