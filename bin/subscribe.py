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

                # 【修正】引数にパスを追加: (socket, sub_id, flags, path)
                # 購読したパス、あるいはその配下の特定のパスを指定します
                modifications = cdb.get_modifications(read_sock, sub_ids[0], 0, "/server-config")

                if not modifications:
                    print("No modifications found.")
                else:
                    for mod in modifications:
                        # mod.tag は [XMLタグのハッシュ値] のリストです。
                        # mod.v は変更後の値 (_confd.Value) です。
                        # _confd.hash2str() を使ってタグを人間が読める文字列に変換します。
                        tag_path = "/".join([_confd.hash2str(t) for t in mod.tag])
                        print(f"Diff Detected! Path: {tag_path}, Value: {str(mod.v)}")

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