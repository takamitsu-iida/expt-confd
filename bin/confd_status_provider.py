#!/usr/bin/env python3

import socket
import _confd
import _confd.dp as dp
from datetime import datetime

# YANGをコンパイルした時に生成された名前空間ファイルをインポート
import server_status_ns as ns

START_TIME = datetime.now()
wrksock_global = None  # コールバックから参照できるように保持

class TransCallbacks:
    def cb_init(self, tctx):
        try:
            # wrksock_global はすでに整数(int)なので、そのまま渡す
            # もし AttributeError が出たら、単に fd = wrksock_global とする
            fd = wrksock_global
            dp.trans_set_fd(tctx, fd)
            print(f"DEBUG: Transaction initialized with FD {fd}")
        except Exception as e:
            print(f"DEBUG callback error: {e}")
            return _confd.ERR
        return _confd.OK

class DataCallbacks:
    def cb_get_elem(self, tctx, kp):
        try:
            # kp[-1] はリクエストされたパスの「一番末尾」の要素です。
            # 例: /server-status/uptime なら uptime のタグ
            tag = kp[-1].tag

            if tag == ns.ns.server_status_uptime:
                val = _confd.Value("Up and running!", _confd.C_STR)
            elif tag == ns.ns.server_status_last_checked_at:
                val = _confd.Value(datetime.now().strftime("%H:%M:%S"), _confd.C_STR)
            else:
                return 2 # NOT_FOUND

            dp.data_reply_value(tctx, val)
            return _confd.OK
        except Exception as e:
            print(f"DEBUG Error: {e}")
            return 1



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