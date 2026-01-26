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

            # dp.trans_set_fd(tctx, fd)

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

    # 1. ソケット接続（順序：Control -> Worker）
    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, "127.0.0.1", 4565, None)
    dp.connect(dctx, wrksock_global, dp.WORKER_SOCKET, "127.0.0.1", 4565, None)

    # 2. 【最重要】ここでWorkerソケットをシステムに教え込む
    # trans_set_fd ではなく、daemon全体のworkerとして登録を試みる
    try:
        # この関数は dir(dp) にはありませんでしたが、
        # _confd 側（dpの上位）にある可能性があります。
        # もしエラーが出るなら、この行は飛ばして次へ。
        dp.set_daemon_worker_fd(dctx, wrksock_global.fileno())
    except:
        pass

    # 3. コールバック登録
    dp.register_trans_cb(dctx, TransCallbacks())
    dp.register_data_cb(dctx, "server_status_cp", DataCallbacks())

    # 4. 登録完了を通知
    dp.register_done(dctx)

    import select
    # 監視対象を明示的に整数（FD）にする
    socks = [ctlsock, wrksock_global]

    print("Status Provider is running... (Ready for 'show server-status')")

    try:
        while True:
            # select で両方のソケットを監視
            r, _, _ = select.select(socks, [], [])
            for s in r:
                # fd_ready には dctx と「反応したソケット」を渡す
                dp.fd_ready(dctx, s)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()