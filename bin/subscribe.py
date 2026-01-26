#!/usr/bin/env python3

import socket
import _confd
import _confd.cdb as cdb
import _confd.maapi as maapi

def run():
    cdb_sock = socket.socket()
    maapi_sock = socket.socket()

    cdb.connect(cdb_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)
    maapi.connect(maapi_sock, '127.0.0.1', 4565)

    # 【最終修正】第5引数はタプルではなく、単なる文字列 "127.0.0.1"
    # 第6引数 (proto) も、このシンプル版APIでは不要、あるいは文字列を期待する可能性があります。
    # まずは引数5つで試します。
    src_addr = '127.0.0.1'

    try:
        # 成功率が最も高い構成：(socket, user, context, groups, ip_string)
        maapi.start_user_session(maapi_sock, 'admin', 'system', ['admin'], src_addr)
    except TypeError:
        # もし引数が足りないと言われた場合のみ、プロトコルを追加
        maapi.start_user_session(maapi_sock, 'admin', 'system', ['admin'], src_addr, 1) # 1 = PROTO_TCP

    sub_id = cdb.subscribe(cdb_sock, 1, 0, '/server-config')
    cdb.subscribe_done(cdb_sock)

    print("Waiting for configuration changes...")

    try:
        while True:
            # 1. 変更通知の待機
            sub_ids = cdb.read_subscription_socket(cdb_sock)

            # 2. CDBから直接値を読み取る (新しいソケットを毎回開かなくてOK)
            # 読み取り専用のセッションを開始
            # cdb.DATA_SOCKET (1) を使い、cdb.RUNNING (1) から取得
            read_sock = socket.socket()
            cdb.connect(read_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

            try:
                # cdb.get(socket, path) で直接値を取得
                val = cdb.get(read_sock, "/server-config/ip-address")
                print(f"DEBUG: val repr -> {repr(val)}")
                print(f"Config Changed! New IP: {str(val)}")
            finally:
                read_sock.close()

            # 3. 通知完了の同期
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        cdb_sock.close()
        maapi_sock.close()

if __name__ == "__main__":
    run()