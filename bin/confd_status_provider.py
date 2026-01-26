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
    dctx = dp.init_daemon("status_provider_daemon")

    ctlsock = socket.socket()
    wrksock = socket.socket()

    # 1. 接続
    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
    dp.connect(dctx, wrksock, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)

    # 2. 【重要】ソケットをContextに登録する
    # これにより "No descriptor set" エラーを解消します
    dp.set_fd(dctx, ctlsock)
    dp.set_fd(dctx, wrksock)

    print("Connected and FDs are set.")

    # 3. コールバック登録 (クラス形式)
    dp.register_trans_cb(dctx, TransCallbacks())
    dp.register_data_cb(dctx, "server_status_cp", DataCallbacks())
    dp.register_done(dctx)

    import select
    socks = [ctlsock, wrksock]

    print("Status Provider is running... (Waiting for show server-status)")

    try:
        while True:
            # タイムアウトを設定して確実にループを回す
            read_socks, _, _ = select.select(socks, [], [], 1.0)

            for s in read_socks:
                try:
                    # 正しい引数順序で処理
                    dp.fd_ready(dctx, s)
                except Exception as e:
                    # エラーが出てもループを止めない
                    print(f"DEBUG Error: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        ctlsock.close()
        wrksock.close()



if __name__ == "__main__":
    run()