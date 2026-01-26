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
    ctlsock = socket.socket()
    wrksock = socket.socket()

    import struct
    # '127.0.0.1' をネットワークバイトオーダの整数に変換
    ip_int = struct.unpack("!I", socket.inet_aton('127.0.0.1'))[0]

    try:
        # 引数3 (IP) は整数 ip_int
        # 引数4 (src_addr) は None (文字列を期待されているが、通常は不要)
        dp.connect(ctlsock, dp.CONTROL_SOCKET, ip_int, 4565, None)
        dp.connect(wrksock, dp.WORKER_SOCKET, ip_int, 4565, None)
    except TypeError:
        # もし引数の数が合わないと言われたら、src_addr を完全に抜く
        dp.connect(ctlsock, dp.CONTROL_SOCKET, ip_int, 4565)
        dp.connect(wrksock, dp.WORKER_SOCKET, ip_int, 4565)

    dctx = dp.init_daemon("status_provider_daemon")
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