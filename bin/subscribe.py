#!/usr/bin/env python3

import socket
import _confd
import _confd.cdb as cdb
import _confd.maapi as maapi

def run():
    cdb_sock = socket.socket()
    maapi_sock = socket.socket()

    cdb.connect(cdb_sock, cdb.DATA_SOCKET, '127.0.0.1', 4565)
    maapi.connect(maapi_sock, '127.0.0.1', 4565)

    # 【最終修正】第5引数はタプルではなく、単なる文字列 "127.0.0.1"
    # 第6引数 (proto) も、このシンプル版APIでは不要、あるいは文字列を期待する可能性があります。
    # まずは引数5つで試します。
    src_addr = '127.0.0.1'

    try:
        # 成功率が最も高い構成：(socket, user, context, groups, ip_string)
        maapi.start_user_session(maapi_sock, 'admin', 'system', ['admin'], src_addr)
    except TypeError:
        # もし引数が足りないと言われた場合のみ、プロトコルを追加
        maapi.start_user_session(maapi_sock, 'admin', 'system', ['admin'], src_addr, 1) # 1 = PROTO_TCP

    sub_id = cdb.subscribe(cdb_sock, 1, 0, '/server-config')
    cdb.subscribe_done(cdb_sock)

    print("Waiting for configuration changes...")

    try:
        while True:
            # 変更通知の待機
            cdb.read_subscription_socket(cdb_sock)

            # トランザクション開始 (1=RUNNING, 1=READ)
            th = maapi.start_trans(maapi_sock, 1, 1)
            try:
                # 値の取得
                val = maapi.get_elem(maapi_sock, th, "/server-config/ip-address")

                # 【修正案A】 _confd.val2str を使って、YANGモデルの定義に基づき文字列化する
                # 第2引数は、その値が定義されているパス（または型情報）を渡します
                out_str = _confd.val2str(((maapi_sock, th), "/server-config/ip-address"), val)
                print(f"Config Changed! New IP: {out_str}")

            except Exception as e:
                # もし val2str が使えない環境（シンプルなAPI）なら、直接 val を出力
                print(f"Raw Value: {val}, Type: {type(val)}")


            finally:
                maapi.finish_trans(maapi_sock, th)

            # 通知完了の同期 (1=DONE_PRIORITY)
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        cdb_sock.close()
        maapi_sock.close()

if __name__ == "__main__":
    run()