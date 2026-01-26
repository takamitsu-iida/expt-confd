#!/usr/bin/env python3

import socket
import _confd
import _confd.cdb as cdb
import _confd.maapi as maapi

def run():
    # 1. 購読用ソケット
    cdb_sock = socket.socket()
    cdb.connect(cdb_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

    # 購読登録
    sub_id = cdb.subscribe(cdb_sock, 1, 0, '/server-config')
    cdb.subscribe_done(cdb_sock)

    print("Waiting for configuration changes...")

    try:
        while True:
            # 2. 通知を待機
            cdb.read_subscription_socket(cdb_sock)

            # 3. データの読み取り用ソケットを別途作成
            read_sock = socket.socket()
            cdb.connect(read_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

            try:
                # 【ここが重要】CDBセッションを開始する
                # 引数: (socket, type=cdb.RUNNING)
                cdb.start_session(read_sock, cdb.RUNNING)

                # 値の取得
                val = cdb.get(read_sock, "/server-config/ip-address")
                print(f"DEBUG: val repr -> {repr(val)}")
                print(f"Config Changed! New IP: {str(val)}")

                # セッションを終了
                cdb.end_session(read_sock)
            finally:
                read_sock.close()

            # 4. 通知完了の同期
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        cdb_sock.close()

if __name__ == "__main__":
    run()