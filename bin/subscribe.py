#!/usr/bin/env python3

import socket
import _confd
import _confd.cdb as cdb

def run():
    # 購読用ソケットのセットアップ
    cdb_sock = socket.socket()
    cdb.connect(cdb_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

    # 監視したいパスをリスト化しておく
    watched_paths = [
        "/server-config/ip-address",
        # 今後項目が増えてもここに追加するだけでOK
    ]

    # 購読登録
    cdb.subscribe(cdb_sock, 1, 0, '/server-config')
    cdb.subscribe_done(cdb_sock)

    print("Waiting for configuration changes (Robust Mode)...")

    try:
        while True:
            # 1. 変更通知を待機
            cdb.read_subscription_socket(cdb_sock)

            # 2. 値を読み取るためのセッションを開始
            read_sock = socket.socket()
            cdb.connect(read_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

            try:
                cdb.start_session(read_sock, cdb.RUNNING)

                print("--- Config Update Detected ---")
                for path in watched_paths:
                    try:
                        val = cdb.get(read_sock, path)
                        print(f"Path: {path} -> Value: {val}")
                    except Exception as e:
                        print(f"Path: {path} -> Not found or Error: {e}")

                cdb.end_session(read_sock)
            finally:
                read_sock.close()

            # 3. 通知完了を報告（これを忘れると次の変更が届きません）
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping...")
        cdb_sock.close()

if __name__ == "__main__":
    run()