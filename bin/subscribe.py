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

    # 【修正】第5引数にログイン元IPアドレスを追加
    # _confd.Address は、タプル (socket.AF_INET, '127.0.0.1') などを期待します
    src_addr = _confd.Address((socket.AF_INET, '127.0.0.1'))
    maapi.start_user_session(maapi_sock, 'admin', 'system', ['admin'], src_addr)

    sub_id = cdb.subscribe(cdb_sock, 1, 0, '/server-config')
    cdb.subscribe_done(cdb_sock)

    print("Waiting for configuration changes...")

    try:
        while True:
            # 変更通知の待機
            sub_ids = cdb.read_subscription_socket(cdb_sock)

            # トランザクション開始 (1=RUNNING, 1=READ)
            th = maapi.start_trans(maapi_sock, 1, 1)
            try:
                # 値の取得
                val = maapi.get_elem(maapi_sock, th, "/server-config/ip-address")
                print(f"Config Changed! New IP: {str(val)}")
            finally:
                maapi.finish_trans(maapi_sock, th)

            # 通知完了の同期 (1=DONE_PRIORITY)
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        cdb_sock.close()
        maapi_sock.close()

if __name__ == "__main__":
    run()