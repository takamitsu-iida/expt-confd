#!/usr/bin/env python3
"""
ConfD ステータスプロバイダーデーモン

このスクリプトはConfDのデータプロバイダーとして動作し、
'show server-status' コマンドで表示されるサーバーステータス情報を提供します。

提供する情報:
- uptime: サーバーの稼働状態メッセージ
- last-checked-at: 最後にチェックした時刻（HH:MM:SS形式）

YANGモデル:
- コールポイント名: server_status_cp
- 名前空間: confd_status_provider_ns
"""

import socket
import sys
from datetime import datetime
from typing import Optional

import select

try:
    import _confd
    import _confd.dp as dp
    import confd_status_provider_ns as ns
except ImportError as e:
    print(f"Error: Could not import required ConfD modules: {e}")
    print("Make sure ConfD is installed and PYTHONPATH is set correctly.")
    sys.exit(1)

# =============================================================================
# 定数定義
# =============================================================================

# ConfD接続設定
CONFD_HOST = "127.0.0.1"
CONFD_PORT = 4565

# コールポイント名（YANGファイルで定義したもの）
CALLPOINT_NAME = "server_status_cp"

# デーモン名
DAEMON_NAME = "status_provider_daemon"

# YANGノードのハッシュ値を取得
# ConfDは内部的にノードをハッシュ値で識別するため、これを使って判定する
UPTIME_HASH = str(ns.ns.ex_uptime)
LAST_CHECKED_HASH = str(ns.ns.ex_last_checked_at)

# デバッグ情報
print(f"INFO: YANG node hashes loaded")
print(f"  - uptime hash: {UPTIME_HASH}")
print(f"  - last-checked-at hash: {LAST_CHECKED_HASH}")

# プロセス起動時刻（uptimeの表示に使用）
START_TIME = datetime.now()

# Workerソケットのグローバル参照
# トランザクションコールバックで使用するため、グローバル変数として保持
wrksock_global: Optional[socket.socket] = None

# =============================================================================
# コールバッククラス
# =============================================================================

class TransCallbacks:
    """
    トランザクション管理用コールバック

    ConfDがトランザクションを開始・終了する際に呼び出されます。
    """

    def cb_init(self, tctx) -> int:
        """
        トランザクション初期化コールバック

        Args:
            tctx: トランザクションコンテキスト

        Returns:
            _confd.OK: 成功
            _confd.ERR: エラー
        """
        try:
            # Workerソケットをトランザクションに紐付ける
            # これにより、ConfDはこのソケットを通じてデータ要求を送信できる
            dp.trans_set_fd(tctx, wrksock_global)
            print("DEBUG: Transaction initialized successfully")
            return _confd.OK
        except Exception as e:
            print(f"ERROR: Transaction initialization failed: {e}")
            return _confd.ERR

    def cb_finish(self, tctx) -> int:
        """
        トランザクション終了コールバック

        Args:
            tctx: トランザクションコンテキスト

        Returns:
            常に _confd.OK
        """
        return _confd.OK


class DataCallbacks:
    """
    データ取得用コールバック

    ConfDが設定値やステータス情報を要求する際に呼び出されます。
    """

    def cb_get_elem(self, tctx, kp) -> int:
        """
        要素取得コールバック

        ConfDが特定のYANGノードの値を要求したときに呼び出されます。

        Args:
            tctx: トランザクションコンテキスト
            kp: キーパス（要求されたYANGノードのパス）

        Returns:
            _confd.OK: データ返却成功
            _confd.CONFD_ERR: エラー発生
            その他の値: ConfDエラーコード（例: NOT_FOUND = 2）
        """
        try:
            path = str(kp)
            print(f"DEBUG: Data request for path: {path}")

            # ハッシュ値を使ってどのノードが要求されたか判定
            if UPTIME_HASH in path:
                # uptime ノード: サーバーの稼働状態を返す
                uptime_msg = self._get_uptime_message()
                val = _confd.Value(uptime_msg, _confd.C_STR)
                dp.data_reply_value(tctx, val)
                print(f"DEBUG: Returned uptime: {uptime_msg}")

            elif LAST_CHECKED_HASH in path:
                # last-checked-at ノード: 現在時刻を返す
                current_time = self._get_current_time()
                val = _confd.Value(current_time, _confd.C_STR)
                dp.data_reply_value(tctx, val)
                print(f"DEBUG: Returned last-checked-at: {current_time}")

            else:
                # 未知のパス
                print(f"WARN: Unknown path requested: {path}")
                # NOT_FOUND (2) を返す
                # 定数インポートのトラブルを避けるため数値を直接使用
                return 2

            return _confd.OK

        except Exception as e:
            print(f"ERROR: Failed to get element: {e}")
            return _confd.ERR

    @staticmethod
    def _get_uptime_message() -> str:
        """
        稼働状態メッセージを取得

        Returns:
            稼働状態を示すメッセージ文字列
        """
        elapsed = datetime.now() - START_TIME
        hours = int(elapsed.total_seconds() // 3600)
        minutes = int((elapsed.total_seconds() % 3600) // 60)

        return f"Up and running! (Uptime: {hours}h {minutes}m)"

    @staticmethod
    def _get_current_time() -> str:
        """
        現在時刻を取得

        Returns:
            HH:MM:SS形式の時刻文字列
        """
        return datetime.now().strftime("%H:%M:%S")


# =============================================================================
# メイン処理
# =============================================================================

def run() -> None:
    """
    ステータスプロバイダーデーモンのメイン処理

    ConfDに接続し、データプロバイダーとして登録してメインループを実行します。
    Ctrl-Cで終了するまで動作を継続します。
    """
    global wrksock_global

    # ConfDデーモンコンテキストを初期化
    print(f"INFO: Initializing daemon: {DAEMON_NAME}")
    dctx = dp.init_daemon(DAEMON_NAME)

    # ソケットを作成
    ctlsock = socket.socket()  # 制御用ソケット
    wrksock_global = socket.socket()  # ワーカー用ソケット

    try:
        # ConfDに接続
        print(f"INFO: Connecting to ConfD at {CONFD_HOST}:{CONFD_PORT}")
        dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, CONFD_HOST, CONFD_PORT, None)
        dp.connect(dctx, wrksock_global, dp.WORKER_SOCKET, CONFD_HOST, CONFD_PORT, None)

        # コールバックを登録
        print("INFO: Registering callbacks")
        dp.register_trans_cb(dctx, TransCallbacks())
        dp.register_data_cb(dctx, CALLPOINT_NAME, DataCallbacks())
        dp.register_done(dctx)

        # メインループ: ソケットからのイベントを待機
        sockets = [ctlsock, wrksock_global]
        print("=" * 60)
        print("Status Provider is ready!")
        print(f"Try running: 'show server-status' in ConfD CLI")
        print("Press Ctrl-C to stop")
        print("=" * 60)

        while True:
            # select()でソケットの読み取り可能状態を監視
            readable, _, _ = select.select(sockets, [], [])

            # 読み取り可能なソケットがあればConfDに通知
            for sock in readable:
                dp.fd_ready(dctx, sock)

    except KeyboardInterrupt:
        print("\nINFO: Shutting down gracefully...")
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        raise
    finally:
        # クリーンアップ
        print("INFO: Closing sockets")
        ctlsock.close()
        if wrksock_global:
            wrksock_global.close()


def main() -> None:
    """エントリーポイント"""
    try:
        run()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()