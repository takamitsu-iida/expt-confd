#!/usr/bin/env python3

import socket
import _confd
import _confd.dp as dp
from datetime import datetime

# YANGをコンパイルした時に生成された名前空間ファイルをインポート
import confd_status_provider_ns as ns

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
            tag = kp[-1].tag
            # print(f"DEBUG: Requested tag ID: {tag}") # 必要に応じて

            # ns.ns クラス内の属性と直接比較
            if tag == ns.ns.ex_uptime:
                val = _confd.Value("Up and running!", _confd.C_STR)
                dp.data_reply_value(tctx, val)

            elif tag == ns.ns.ex_last_checked_at:
                now_str = datetime.now().strftime("%H:%M:%S")
                val = _confd.Value(now_str, _confd.C_STR)
                dp.data_reply_value(tctx, val)

            else:
                # 2 = NOT_FOUND (見つからない場合に ConfD を待たせない)
                return 2

            return _confd.OK

        except Exception as e:
            print(f"DEBUG Error: {e}")
            return 1 # _confd.ERR

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
            # タイムアウトを短く設定し、確実に回す
            read_socks, _, _ = select.select(socks, [], [], 0.1)

            for s in read_socks:
                try:
                    # ここで dp.fd_ready を呼ぶことで、
                    # ConfD が cb_get_elem を呼び出すトリガーになります
                    dp.fd_ready(dctx, s)
                except Exception as e:
                    print(f"DEBUG fd_ready error: {e}")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()