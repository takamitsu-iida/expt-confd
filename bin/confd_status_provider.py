#!/usr/bin/env python3

import socket
import _confd
import _confd.dp as dp
from datetime import datetime

START_TIME = datetime.now()
wrksock_global = None  # コールバックから参照できるように保持

class TransCallbacks:
    def cb_init(self, tctx):
        # --- ここが最重要：Workerソケットをトランザクションに紐付ける ---
        try:
            dp.trans_set_fd(tctx, wrksock_global)
        except Exception as e:
            print(f"DEBUG: Failed to set trans FD: {e}")
        return _confd.OK

    def cb_finish(self, tctx):
        return _confd.OK

class DataCallbacks:
    def cb_get_elem(self, tctx, kp):
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
    global wrksock_global
    dctx = dp.init_daemon("status_provider_daemon")

    ctlsock = socket.socket()
    wrksock_global = socket.socket()

    # 1. ソケット接続 (この API では登録より先に行う必要がある)
    # 引数はこれまでに成功した 6引数シグネチャを想定
    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
    dp.connect(dctx, wrksock_global, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)
    print("Connected successfully!")

    # 2. コールバック登録 (接続後に行う)
    dp.register_trans_cb(dctx, TransCallbacks())
    dp.register_data_cb(dctx, "server_status_cp", DataCallbacks())
    dp.register_done(dctx)

    import select
    socks = [ctlsock, wrksock_global]
    print("Status Provider is running... (Ready for 'show server-status')")

    try:
        while True:
            read_socks, _, _ = select.select(socks, [], [])
            for s in read_socks:
                # Daemon Context とソケットを渡してリクエストを処理
                dp.fd_ready(dctx, s)
    except KeyboardInterrupt:
        pass
    finally:
        ctlsock.close()
        wrksock_global.close()

if __name__ == "__main__":
    run()