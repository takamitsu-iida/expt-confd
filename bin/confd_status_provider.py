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
    # 1. 最初に Daemon Context を作成
    dctx = dp.init_daemon("status_provider_daemon")

    ctlsock = socket.socket()
    wrksock = socket.socket()

    # 接続テスト：引数の順番を大胆に入れ替えます
    # 1:dctx, 2:sock, 3:type, 4:ip(str), 5:port(int), 6:src_addr(None)
    try:
        print("Trying signature: (dctx, sock, type, ip_str, port_int, None)")
        dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
        dp.connect(dctx, wrksock, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)
    except TypeError as e:
        print(f"6-arg failed: {e}")
        # もし引数の数が多いと言われたら、最後を削る
        print("Trying signature: (dctx, sock, type, ip_str, port_int)")
        dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565)
        dp.connect(dctx, wrksock, dp.WORKER_SOCKET, "127.0.0.1", 4565)

    # 2. コールバック登録
    cbs = dp.DataCallbacks()
    cbs.get_elem = get_elem_callback
    dp.register_data_cb(dctx, "server_status_cp", cbs)
    dp.register_done(dctx)

    print("Status Provider is running...")

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