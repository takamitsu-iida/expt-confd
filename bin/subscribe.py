#!/usr/bin/env python3

import socket
import confd.cdb as cdb
import confd.maapi as maapi

def run():
    # 1. ソケットを作成して接続
    # CDB通知用
    cdb_sock = socket.socket()
    # MAAPI用
    maapi_sock = socket.socket()

    # 2. クラスをインスタンス化（モジュール名と同じ小文字の cdb.cdb / maapi.maapi）
    # APIのバージョンによっては、ここがインスタンス化の入り口になります
    c = cdb.cdb(cdb_sock)
    m = maapi.maapi(maapi_sock)

    # 3. インスタンスメソッドとしてconnectを呼び出し
    # 第2引数はCDB_DATA_SOCKET (通常 1)
    c.connect('127.0.0.1', 4565, 1)
    m.connect('127.0.0.1', 4565)

    # 4. 購読の登録
    # 第1引数: 優先度(1), 第2引数: ID(0), 第3引数: パス
    c.subscribe(1, 0, '/server-config')
    c.subscribe_done()

    print("Waiting for configuration changes...")

    try:
        while True:
            # 5. 通知の待機 (ソケットをセレクト)
            c.read_subscription_socket()

            # 6. 変更内容の読み取り
            # cdb.RUNNING=1, maapi.READ=1
            th = m.start_trans(1, 1)
            try:
                val = m.get_elem(th, "/server-config/ip-address")
                print(f"Config Changed! New IP: {val}")
            finally:
                m.finish_trans(th)

            # 7. 通知の完了報告 (cdb.DONE_PRIORITY=1)
            c.sync_subscription_socket(1)

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        cdb_sock.close()
        maapi_sock.close()

if __name__ == "__main__":
    run()