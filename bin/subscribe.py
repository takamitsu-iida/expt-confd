#!/usr/bin/env python3

import socket
import confd.cdb as cdb
import confd.maapi as maapi

def run():
    # 1. ConfDへの接続
    sock = socket.socket()
    cdb.connect(sock, cdb.CDB_DATA_SOCKET, '127.0.0.1', 4565)

    # 2. 購読の登録 (監視するパスを指定)
    # /server-config 以下の変更を監視
    sub = cdb.Subscriber(sock)
    sub_id = sub.subscribe('/server-config', 1)
    sub.subscribe_done()

    print("Waiting for configuration changes...")

    try:
        while True:
            # 3. 通知の待機 (ブロッキング)
            sel = [sock]
            if sock in sel:
                # 変更があったパスのリストを取得
                sub_ids = sub.read()

                # 4. 変更内容の読み取り
                # 実際の値を取得するには MAAPI を使うのが一般的
                with maapi.Maapi() as m:
                    m.connect(socket.socket(), '127.0.0.1', 4565)
                    with m.start_read_trans() as th:
                        val = m.get_elem(th, "/server-config/ip-address")
                        print(f"Config Changed! New IP: {val}")

                # 5. 通知の確認（ConfDに変更完了を伝える）
                sub.ack()

    except KeyboardInterrupt:
        sock.close()

if __name__ == "__main__":
    run()