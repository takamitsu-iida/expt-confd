#!/usr/bin/env python3

import select
import socket
import _confd
import _confd.dp as dp
import time
from datetime import datetime

# 起動時刻を記録
START_TIME = datetime.now()

# --- 1. コールバック用クラスの定義 ---
class TransCallbacks:
    # 辞書ではなくメソッドとして定義
    def cb_init(self, tctx):
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
    # 1. 先に Daemon Context を作成
    dctx = dp.init_daemon("status_provider_daemon")

    # 2. 【重要】接続の前にコールバックを登録してしまう
    dp.register_trans_cb(dctx, TransCallbacks())
    dp.register_data_cb(dctx, "server_status_cp", DataCallbacks())

    # 3. ここでソケット作成と接続
    ctlsock = socket.socket()
    wrksock = socket.socket()
    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
    dp.connect(dctx, wrksock, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)

    # 4. register_done を呼ぶ（ここで内部的にWorkerが紐付くことが多い）
    dp.register_done(dctx)

    print("Registration and Connection completed.")

    import select
    socks = [ctlsock, wrksock]
    print("Status Provider is running... (Ready for show server-status)")

    try:
        while True:
            read_socks, _, _ = select.select(socks, [], [])
            for s in read_socks:
                # エラーが出たときの fd_ready の呼び出し
                dp.fd_ready(dctx, s)
    except KeyboardInterrupt:
        pass
    finally:
        ctlsock.close()
        wrksock.close()



if __name__ == "__main__":
    run()