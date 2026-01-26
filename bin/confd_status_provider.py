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
    # 1. まず先に Daemon Context を作成する
    dctx = dp.init_daemon("status_provider_daemon")

    ctlsock = socket.socket()
    wrksock = socket.socket()

    import struct
    ip_int = struct.unpack("!I", socket.inet_aton('127.0.0.1'))[0]

    try:
        # 【重要】第1引数に dctx を入れる
        # 仕様例: dp.connect(dctx, socket, type, ip, port)
        dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, ip_int, 4565)
        dp.connect(dctx, wrksock, dp.WORKER_SOCKET, ip_int, 4565)
        print("Connected using dctx-first signature.")
    except TypeError:
        # もし上記でもダメな場合、以前の ip_int の位置に dctx を要求している可能性
        dp.connect(ctlsock, dp.CONTROL_SOCKET, dctx, ip_int, 4565)
        dp.connect(wrksock, dp.WORKER_SOCKET, dctx, ip_int, 4565)
        print("Connected using dctx-third signature.")

    # 2. コールバック登録
    cbs = dp.DataCallbacks()
    cbs.get_elem = get_elem_callback
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