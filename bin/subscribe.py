#!/usr/bin/env python3

import socket
import _confd
import _confd.cdb as cdb

# 差分が見つかるたびに呼び出される「コールバック関数」
def diff_recorder(kp, op, oldv, newv, state):
    # kp: キーパス（変更された場所）
    # op: 操作の種類 (MOP_CREATED, MOP_VALUE_SET, MOP_DELETED など)
    # oldv: 変更前の値
    # newv: 変更後の値

    path = str(kp)
    operation = "SET" if op == _confd.MOP_VALUE_SET else "OTHER"

    print(f"  [Iterate] Path: {path}")
    print(f"  [Iterate] Operation: {operation}, New Value: {newv}")

    return _confd.ITER_RECURSE

def run():
    cdb_sock = socket.socket()
    cdb.connect(cdb_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

    # 購読の登録
    sub_id = cdb.subscribe(cdb_sock, 1, 0, '/server-config')
    cdb.subscribe_done(cdb_sock)

    print("Waiting for configuration changes (using diff_iterate)...")

    try:
        while True:
            sub_ids = cdb.read_subscription_socket(cdb_sock)

            # 差分解析用のセッション
            read_sock = socket.socket()
            cdb.connect(read_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)

            try:
                cdb.start_session(read_sock, cdb.RUNNING)

                # 【今回の主役】 diff_iterate
                # 変更があった箇所だけを自動的にスキャンして diff_recorder を呼び出します
                # 引数: (socket, sub_id, callback, flags, state)
                cdb.diff_iterate(read_sock, sub_ids[0], diff_recorder, 0, None)

                cdb.end_session(read_sock)
            finally:
                read_sock.close()

            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping...")
        cdb_sock.close()

if __name__ == "__main__":
    run()