#!/usr/bin/env python3

import socket
import _confd
import _confd.cdb as cdb
import _confd.maapi as maapi

import socket
import _confd
import _confd.cdb as cdb
import _confd.maapi as maapi

def run():
    cdb_sock = socket.socket()
    maapi_sock = socket.socket()

    cdb.connect(cdb_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)
    maapi.connect(maapi_sock, '127.0.0.1', 4565)

    # 【修正】_confd.Address を使わず、直接タプルでアドレスを指定
    # 形式: (socket.AF_INET, '127.0.0.1')
    # ポートを含める必要がある場合は (socket.AF_INET, '127.0.0.1', 0)
    src_addr = (socket.AF_INET, '127.0.0.1')

    try:
        maapi.start_user_session(maapi_sock, 'admin', 'system', ['admin'], src_addr, _confd.PROTO_TCP)
    except TypeError:
        # 万が一、引数の数がさらに多い・少ない場合のためのフォールバック
        maapi.start_user_session(maapi_sock, 'admin', 'system', ['admin'], src_addr)

    sub_id = cdb.subscribe(cdb_sock, 1, 0, '/server-config')
    cdb.subscribe_done(cdb_sock)

    print("Waiting for configuration changes...")

    try:
        while True:
            sub_ids = cdb.read_subscription_socket(cdb_sock)

            # RUNNING=1, READ=1
            th = maapi.start_trans(maapi_sock, 1, 1)
            try:
                val = maapi.get_elem(maapi_sock, th, "/server-config/ip-address")
                # val がオブジェクトなら str()、そうでなければそのまま表示
                print(f"Config Changed! New IP: {val}")
            finally:
                maapi.finish_trans(maapi_sock, th)

            # DONE_PRIORITY=1
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        cdb_sock.close()
        maapi_sock.close()

if __name__ == "__main__":
    run()