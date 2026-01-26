#!/usr/bin/env python3

import socket
import confd.cdb as cdb
import confd.maapi as maapi

def run():
    # 1. ソケットの作成と接続
    # CDBの通知を受け取るためのソケット
    sock = socket.socket()
    # cdb.connect は cdb モジュール直下の関数として呼び出します
    cdb.connect(sock, cdb.CDB_DATA_SOCKET, '127.0.0.1', 4565)

    # 2. 購読の登録
    # 接続したソケットを使って購読を開始
    sub_id = cdb.subscribe(sock, 1, 0, '/server-config')
    cdb.subscribe_done(sock)

    print("Waiting for configuration changes...")

    try:
        while True:
            # 3. 通知の待機 (CDBからの通知を読み取る)
            # 戻り値には通知の種類や購読IDが含まれます
            sub_ids = cdb.read_subscription_socket(sock)

            # 4. 変更内容の読み取り (MAAPIを使用)
            # MAAPI用のソケットを別途作成
            m_sock = socket.socket()
            maapi.connect(m_sock, '127.0.0.1', 4565)

            # 読み取りトランザクションの開始
            # cdb.RUNNING は通常 1 です
            th = maapi.start_trans(m_sock, cdb.RUNNING, maapi.READ)
            try:
                # 値の取得
                val = maapi.get_elem(m_sock, th, "/server-config/ip-address")
                print(f"Config Changed! New IP: {val}")
            finally:
                maapi.finish_trans(m_sock, th)
                m_sock.close()

            # 5. 通知の確認 (これを行わないと次の commit が終わらなくなります)
            cdb.sync_subscription_socket(sock, cdb.DONE_PRIORITY)

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        sock.close()

if __name__ == "__main__":
    run()