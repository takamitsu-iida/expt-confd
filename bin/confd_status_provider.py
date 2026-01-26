#!/usr/bin/env python3

import socket
import _confd
import _confd.dp as dp
from datetime import datetime

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
            path = str(kp)
            print(f"DEBUG: Requested path: {path}")

            # ハッシュIDでの判定が最も確実です
            if "1268395647" in path: # uptime
                val = _confd.Value("Up and running!", _confd.C_STR)
            elif "103640840" in path: # last-checked-at
                val = _confd.Value(datetime.now().strftime("%H:%M:%S"), _confd.C_STR)
            else:
                # 最終手段：定数が見つからない場合は、直接数値を返すか
                # _confd.ERR_NOT_FOUND などを試す
                # 多くの環境では _confd.NOT_FOUND ですが、エラーが出るなら以下を試してください
                return 2 # 2 は ConfD における NOT_FOUND の値です

            dp.data_reply_value(tctx, val)
            return _confd.OK
        except Exception as e:
            print(f"DEBUG get_elem error: {e}")
            # エラー時は _confd.ERR (通常は 1)
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