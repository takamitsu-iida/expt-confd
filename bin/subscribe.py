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

                for mod in modifications:
                    # 初回は属性を確認するために print(dir(mod)) を入れると確実です
                    print(f"DEBUG: mod attributes -> {dir(mod)}")

                    # 一般的な _confd の構造
                    try:
                        # タグ（パス）と値を取り出す
                        t = mod.tag
                        v = mod.val if hasattr(mod, 'val') else mod.v
                        print(f"Diff Detected! Path Tag: {t}, Value: {v}")
                    except Exception as e:
                        print(f"Could not parse mod: {e}")


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