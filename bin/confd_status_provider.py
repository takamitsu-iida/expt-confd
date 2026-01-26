#!/usr/bin/env python3

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

    # 接続処理（成功したものを継続）
    ctlsock = socket.socket()
    wrksock = socket.socket()
    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
    dp.connect(dctx, wrksock, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)
    print("Connected successfully!")

    # --- 2. クラスのインスタンスを登録 ---
    # 辞書 {'cb_init': ...} ではなく、オブジェクトそのものを渡します
    dp.register_trans_cb(dctx, TransCallbacks())

    # データコールバックも同様にクラスで登録
    # メソッド名が cb_get_elem になっていることに注目
    dp.register_data_cb(dctx, "server_status_cp", DataCallbacks())

    dp.register_done(dctx)

    print("Status Provider is running... (Waiting for show server-status)")

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