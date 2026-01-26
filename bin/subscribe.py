#!/usr/bin/env python3

import socket
import _confd
import _confd.cdb as cdb
import _confd.maapi as maapi

def run():
    # 1. ソケットの作成
    cdb_sock = socket.socket()
    maapi_sock = socket.socket()

    # 2. 接続 (低レイヤAPIの _confd.cdb.connect を使用)
    # 引数: (socket, type, ip, port)
    cdb.connect(cdb_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)
    maapi.connect(maapi_sock, '127.0.0.1', 4565)

    # 3. 購読の登録
    # 引数: (socket, priority, 0, path)
    sub_id = cdb.subscribe(cdb_sock, 1, 0, '/server-config')
    cdb.subscribe_done(cdb_sock)

    print("Waiting for configuration changes...")

    try:
        while True:
            # 4. 通知の待機
            # 変更があった購読IDのリストが返ります
            sub_ids = cdb.read_subscription_socket(cdb_sock)

            # 5. 変更内容の読み取り (MAAPI)
            # 1 = RUNNING, 1 = READ
            th = maapi.start_trans(maapi_sock, 1, 1)
            try:
                # get_elem は内部形式の Value を返すため str() で変換
                val = maapi.get_elem(maapi_sock, th, "/server-config/ip-address")
                print(f"Config Changed! New IP: {str(val)}")
            finally:
                maapi.finish_trans(maapi_sock, th)

            # 6. 通知の完了報告 (1 = DONE_PRIORITY)
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        cdb_sock.close()
        maapi_sock.close()

if __name__ == "__main__":
    run()