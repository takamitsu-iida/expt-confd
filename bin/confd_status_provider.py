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
    # socks = [ctlsock, wrksock_global]
    # 修正後: ファイル記述子(int)のリストにする
    socks = [ctlsock.fileno(), wrksock_global.fileno()]

    # 辞書を作っておくと、fd からソケットオブジェクトを逆引きできて便利です
    fd_map = {ctlsock.fileno(): ctlsock, wrksock_global.fileno(): wrksock_global}

    print("Status Provider is running... (Ready for 'show server-status')")

    try:
        while True:
            r, _, _ = select.select(socks, [], [])
            for fd in r:
                # 反応した FD に対応するソケットを fd_ready に渡す
                dp.fd_ready(dctx, fd_map[fd])
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()