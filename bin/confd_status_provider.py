#!/usr/bin/env python3

import select
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
            # コメントアウトを解除し、この順序で呼び出す
            # 多くの ConfD バージョンでは (tctx, fd) です
            dp.trans_set_fd(tctx, wrksock_global)

            # もし上記で再びエラーが出る場合は、この順序(fd, tctx)も試してください
            # dp.trans_set_fd(wrksock_global, tctx)

            print(f"DEBUG: Transaction initialized")
            return _confd.OK
        except Exception as e:
            print(f"DEBUG callback error: {e}")
            return _confd.ERR

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

    # 1. 接続
    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
    dp.connect(dctx, wrksock_global, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)

    # 2. コールバック登録
    dp.register_trans_cb(dctx, TransCallbacks())
    dp.register_data_cb(dctx, "server_status_cp", DataCallbacks())
    dp.register_done(dctx)

    # 3. ファイル記述子（整数）を直接取得して監視対象にする
    # connectの後に取得するのがポイントです
    try:
        ctl_fd = ctlsock.fileno()
        wrk_fd = wrksock_global.fileno()
    except AttributeError:
        # すでに整数に置き換わっている場合
        ctl_fd = ctlsock
        wrk_fd = wrksock_global

    socks = [ctl_fd, wrk_fd]
    print(f"Status Provider is running... (CTL FD: {ctl_fd}, WRK FD: {wrk_fd})")

    try:
        while True:
            # タイムアウト(1秒)を設定して、ループが死んでいないか確認しやすくする
            r, _, _ = select.select(socks, [], [], 1.0)
            if not r:
                continue # タイムアウト時は何もしない

            for fd in r:
                # ソケットオブジェクトではなく、整数FDをそのまま渡す
                # これにより、API内部での型変換トラブルを回避します
                dp.fd_ready(dctx, fd)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run()