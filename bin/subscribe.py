#!/usr/bin/env python3

import socket
import _confd
import _confd.cdb as cdb

# 1. コールバック関数をより厳格に定義
def diff_recorder(kp, op, oldv, newv, state):
    try:
        # kp (KeyPath) は通常、ハッシュのタプルかオブジェクトです
        path = str(kp)

        # 値の表示 (None の可能性も考慮)
        new_val = str(newv) if newv is not None else "None"

        print(f"  [Iterate] Path: {path}")
        print(f"  [Iterate] Value: {new_val}")

    except Exception as e:
        print(f"Error in callback: {e}")

    # 【重要】戻り値は必ず _confd の定数 (整数) である必要があります
    return _confd.ITER_RECURSE

def run():
    # 接続用ソケット
    cdb_sock = socket.socket()
    cdb.connect(cdb_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

    # 購読
    cdb.subscribe(cdb_sock, 1, 0, '/server-config')
    cdb.subscribe_done(cdb_sock)

    print("Waiting for configuration changes...")

    try:
        while True:
            # 通知を待機
            sub_ids = cdb.read_subscription_socket(cdb_sock)

            # 読み取り専用ソケット
            read_sock = socket.socket()
            cdb.connect(read_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

            try:
                cdb.start_session(read_sock, cdb.RUNNING)

                # 第5引数 (state) に None ではなく、空のリストや数値を渡してみます
                cdb.diff_iterate(read_sock, sub_ids[0], diff_recorder, 0, [])

                cdb.end_session(read_sock)
            finally:
                read_sock.close()

            # 同期
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping...")
        cdb_sock.close()
    except _confd.error.EOF:
        print("Error: ConfD disconnected. Check if the callback function signature is correct.")

if __name__ == "__main__":
    run()