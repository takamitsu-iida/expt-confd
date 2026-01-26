#!/usr/bin/env python3

import socket
import confd.cdb as cdb
import confd.maapi as maapi

def run():
    # 1. ConfDへの接続 (新しい書き方)
    # Cdbオブジェクトを作成し、connectメソッドを呼び出す
    c = cdb.Cdb()
    c.connect('127.0.0.1', 4565)

    # 2. 購読の登録
    # c.new_subscriber() を使用します
    sub = c.new_subscriber()
    # YANGで定義したパスを指定。第2引数の1は優先度（priority）です
    sub.subscribe('/server-config', 1)
    sub.subscribe_done()

    print("Waiting for configuration changes...")

    try:
        while True:
            # 3. 通知の待機 (Cdbのソケットを使用してselect)
            # sub.read() は通知が来るまでブロックします
            sub_ids = sub.read()

            # 4. 変更内容の読み取り
            # MAAPIを使用して値を取得
            with maapi.Maapi() as m:
                m.connect('127.0.0.1', 4565)
                # 読み取り用のトランザクションを開始
                with m.start_read_trans(db=cdb.RUNNING) as th:
                    val = m.get_elem(th, "/server-config/ip-address")
                    print(f"Config Changed! New IP: {val}")

            # 5. 通知の確認（必須：これをしないと次のcommitがブロックされます）
            sub.ack()

    except KeyboardInterrupt:
        print("\nStopping subscriber...")
        # 接続のクローズなどはコンテキストマネージャや明示的な終了処理で行うのが理想的です

if __name__ == "__main__":
    run()