#!/usr/bin/env python3

import socket
import _confd
import _confd.dp as dp
import time
from datetime import datetime

# 起動時刻を記録
START_TIME = datetime.now()

# --- 1. トランザクション用コールバック (必須) ---
def trans_init(tctx):
    # トランザクション開始時の処理（今回は特に何もしない）
    # 返り値は OK である必要があります
    return _confd.OK

def trans_finish(tctx):
    # トランザクション終了時の処理
    return _confd.OK

# --- 2. データ取得用コールバック ---
def get_elem_callback(tctx, kp):
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

    # ソケット作成と接続 (成功したシグネチャを使用)
    ctlsock = socket.socket()
    wrksock = socket.socket()
    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
    dp.connect(dctx, wrksock, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)
    print("Connected successfully!")

    # --- 3. トランザクションコールバックの登録 ---
    # ここに trans_init と trans_finish を含めるのがポイントです
    trans_cbs = {
        'cb_init': trans_init,
        'cb_finish': trans_finish
    }

    try:
        dp.register_trans_cb(dctx, trans_cbs)
    except Exception:
        # 万が一 cb_finish でエラーが出た場合は 'finish' に戻してください
        trans_cbs = {'cb_init': trans_init, 'finish': trans_finish}
        dp.register_trans_cb(dctx, trans_cbs)

    # --- 4. データコールバックの登録 ---
    data_cbs = {
        'get_elem': get_elem_callback
    }
    dp.register_data_cb(dctx, "server_status_cp", data_cbs)

    dp.register_done(dctx)

    print("Status Provider is running... (Ready for show commands)")

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