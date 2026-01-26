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

            # 1. 変更通知の待機
            sub_ids = cdb.read_subscription_socket(cdb_sock)

            # 2. データの読み取り用ソケット
            read_sock = socket.socket()
            cdb.connect(read_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

            try:
                cdb.start_session(read_sock, cdb.RUNNING)

                # 【ここがポイント】変更された差分をリストで取得
                # 引数: (socket, subscription_id, flags)
                # sub_ids[0] には現在通知された購読IDが入っています
                modifications = cdb.get_modifications(read_sock, sub_ids[0], 0)

                for mod in modifications:
                    # mod はタグのリスト(パス)と値のオブジェクトで構成されます
                    # パスを文字列に変換
                    path_str = _confd.hash2str(mod.tag) # ハッシュ形式の場合
                    # 実際には mod オブジェクトの構造は環境に依存しますが、
                    # 一般的には mod.tag (パス) と mod.val (値) を持ちます
                    print(f"Diff Detected! Path: {mod.tag}, New Value: {mod.val}")

                cdb.end_session(read_sock)
            finally:
                read_sock.close()

            # 3. 通知完了の同期
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        cdb_sock.close()

if __name__ == "__main__":
    run()