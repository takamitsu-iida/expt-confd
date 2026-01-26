#!/usr/bin/env python3

import socket
import _confd
import _confd.dp as dp
from datetime import datetime
import select


# --- ハッシュ値の動的取得 ---
# 文字列からハッシュ値を計算して変数に格納
# ※ str2hash は整数を返すので、比較しやすいように str() で囲むか、
# 後続の path 判定を工夫します。
UPTIME_HASH = str(_confd.str2hash("uptime"))
LAST_CHECKED_HASH = str(_confd.str2hash("last-checked-at"))

print(f"DEBUG: Loaded hashes - uptime: {UPTIME_HASH}, last-checked: {LAST_CHECKED_HASH}")
# ---------------------------

START_TIME = datetime.now()
wrksock_global = None

class TransCallbacks:
    def cb_init(self, tctx):
        try:
            # トランザクション開始時に、Workerソケットを紐付ける
            # ここではソケットオブジェクトを直接渡します
            dp.trans_set_fd(tctx, wrksock_global)
            print(f"DEBUG: Transaction initialized")
            return _confd.OK
        except Exception as e:
            print(f"DEBUG cb_init error: {e}")
            return _confd.ERR

    def cb_finish(self, tctx):
        return _confd.OK

class DataCallbacks:
    def cb_get_elem(self, tctx, kp):
        try:
            path = str(kp)
            print(f"DEBUG: Requested path: {path}")

            # ハッシュIDを直接使って判定（確実な方法）
            if UPTIME_HASH in path: # uptime
                val = _confd.Value("Up and running!", _confd.C_STR)
                dp.data_reply_value(tctx, val)
            elif LAST_CHECKED_HASH in path: # last-checked-at
                now_str = datetime.now().strftime("%H:%M:%S")
                val = _confd.Value(now_str, _confd.C_STR)
                dp.data_reply_value(tctx, val)
            else:
                # 定数トラブルを避けるため、数値を直接返す
                # 2 は NOT_FOUND です
                return 2

            return _confd.OK
        except Exception as e:
            print(f"DEBUG cb_get_elem error: {e}")
            return _confd.ERR

def run():
    global wrksock_global
    dctx = dp.init_daemon("status_provider_daemon")

    ctlsock = socket.socket()
    wrksock_global = socket.socket()

    # 1. ソケット接続
    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
    dp.connect(dctx, wrksock_global, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)

    # 2. コールバック登録
    dp.register_trans_cb(dctx, TransCallbacks())
    dp.register_data_cb(dctx, "server_status_cp", DataCallbacks())
    dp.register_done(dctx)

    # 3. メインループ (ソケットオブジェクトをそのまま使う)
    socks = [ctlsock, wrksock_global]
    print("Status Provider is running... (Ready for 'show server-status')")

    try:
        while True:
            # オブジェクトそのものを渡すことで AttributeError を回避
            r, _, _ = select.select(socks, [], [])
            for s in r:
                dp.fd_ready(dctx, s)
    except KeyboardInterrupt:
        pass
    finally:
        ctlsock.close()
        wrksock_global.close()

if __name__ == "__main__":
    run()