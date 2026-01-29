#!/usr/bin/env python3
"""
ConfD設定変更監視デーモン

このスクリプトはConfDの設定変更を監視し、変更があった場合にログに記録します。
デーモンとして起動することも、フォアグラウンドで実行することも可能です。

使用方法:
    --start      : デーモンとして起動
    --stop       : デーモンを停止
    --status     : デーモンの状態を確認
    --foreground : フォアグラウンドで実行（テスト用）
"""

import argparse
import atexit
import os
import signal
import socket
import sys
import time

from pathlib import Path
from typing import List, Optional

try:
    import _confd.cdb as cdb
except ImportError:
    print("Error: Could not import _confd.cdb module. Make sure ConfD is installed and PYTHONPATH is set correctly.")
    sys.exit(1)

# =============================================================================
# 定数定義
# =============================================================================

# スクリプトのファイル名の拡張子を取り除いた名前
# SCRIPT_BASE = Path(__file__).

# スクリプトのディレクトリを基準にパスを設定
SCRIPT_DIR = Path(__file__).resolve().parent.parent

TMP_DIR = SCRIPT_DIR / 'tmp'
LOG_DIR = SCRIPT_DIR / 'log'

# PIDファイルとログファイルのパス
PID_FILE = TMP_DIR / 'subscribe.pid'
LOG_FILE = LOG_DIR / 'subscribe.log'

# ConfD接続設定
CONFD_HOST = '127.0.0.1'
CONFD_PORT = 4565

# 監視対象のパス（新しいパスはここに追加）
WATCHED_PATHS = [
    "/server-config/ip-address",
    # 今後の監視対象をここに追加
]

# =============================================================================
# デーモン管理関数
# =============================================================================

def daemonize() -> None:
    """
    プロセスをデーモン化する

    二重forkを使用してデーモンプロセスを作成し、
    標準入出力をログファイルにリダイレクトします。
    """
    # ディレクトリを作成（存在しない場合）
    TMP_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

    # 1回目のfork - 親プロセスから分離
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)  # 親プロセスを終了
    except OSError as e:
        sys.stderr.write(f"fork #1 failed: {e}\n")
        sys.exit(1)

    # セッションリーダーになる
    os.chdir('/')
    os.setsid()
    os.umask(0)

    # 2回目のfork - 制御端末から完全に切り離す
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #2 failed: {e}\n")
        sys.exit(1)

    # 標準入出力をログファイルにリダイレクト
    sys.stdout.flush()
    sys.stderr.flush()

    with open(str(LOG_FILE), 'a') as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())

    # PIDファイルを作成
    with open(str(PID_FILE), 'w') as f:
        f.write(str(os.getpid()))

    # 終了時にPIDファイルを削除
    atexit.register(cleanup_pid_file)


def cleanup_pid_file() -> None:
    """PIDファイルを削除する"""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def get_pid() -> Optional[int]:
    """
    PIDファイルからプロセスIDを取得する

    Returns:
        プロセスID、またはPIDファイルが存在しない場合はNone
    """
    try:
        with open(PID_FILE, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def is_running(pid: Optional[int]) -> bool:
    """
    指定されたPIDのプロセスが実行中かチェックする

    Args:
        pid: チェックするプロセスID

    Returns:
        プロセスが実行中の場合True
    """
    if pid is None:
        return False
    try:
        os.kill(pid, 0)  # シグナル0は存在チェックのみ
        return True
    except OSError:
        return False


def start_daemon() -> None:
    """デーモンを起動する"""
    pid = get_pid()
    if is_running(pid):
        print(f"Subscribe daemon is already running (PID: {pid})")
        sys.exit(1)

    # 古いPIDファイルを削除
    cleanup_pid_file()

    print("Starting subscribe daemon...")
    print(f"Log file: {LOG_FILE}")

    daemonize()
    run_subscription_loop()


def stop_daemon() -> None:
    """デーモンを停止する"""
    pid = get_pid()
    if not is_running(pid):
        print("Subscribe daemon is not running")
        cleanup_pid_file()
        sys.exit(1)

    print(f"Stopping subscribe daemon (PID: {pid})...")
    try:
        # TERMシグナルを送信してグレースフルシャットダウン
        os.kill(pid, signal.SIGTERM)

        # プロセスが終了するまで最大5秒待つ
        for _ in range(10):
            if not is_running(pid):
                break
            time.sleep(0.5)

        # まだ実行中の場合は強制終了
        if is_running(pid):
            print("Daemon did not stop gracefully, forcing...")
            os.kill(pid, signal.SIGKILL)

        print("Daemon stopped")
        cleanup_pid_file()
    except Exception as e:
        print(f"Error stopping daemon: {e}")
        sys.exit(1)


def status_daemon() -> None:
    """デーモンのステータスを表示する"""
    pid = get_pid()
    if is_running(pid):
        print(f"Subscribe daemon is running (PID: {pid})")
        print(f"Log file: {LOG_FILE}")
    else:
        print("Subscribe daemon is not running")
        cleanup_pid_file()

# =============================================================================
# ConfD購読処理
# =============================================================================

def setup_subscription(sock: socket.socket, paths: List[str]) -> None:
    """
    ConfDの購読を設定する

    Args:
        sock: ConfD接続用のソケット
        paths: 監視対象のパスリスト
    """
    for path in paths:
        cdb.subscribe(sock, 1, 0, path)

    cdb.subscribe_done(sock)
    print(f"Subscribed to {len(paths)} configuration paths")


def read_full_configuration() -> None:
    """
    設定の全文を読み取って表示する
    """
    read_sock = socket.socket()
    cdb.connect(read_sock, cdb.DATA_SOCKET, CONFD_HOST, CONFD_PORT)

    try:
        cdb.start_session(read_sock, cdb.RUNNING)

        print("--- Full Configuration Dump ---")

        # ルートから設定全体を取得
        try:
            # save_config()を使用して設定全体を取得
            config_data = cdb.save_config(read_sock, cdb.RUNNING, "/")
            print(config_data.decode('utf-8') if isinstance(config_data, bytes) else config_data)
        except AttributeError:
            # save_configが使えない場合は、get_objectを使用
            try:
                obj = cdb.get_object(read_sock, "/")
                print(f"Configuration object: {obj}")
            except Exception as e:
                print(f"Could not retrieve full config: {e}")
                # フォールバック: 監視対象パスのみ表示
                print("\nFalling back to watched paths:")
                for path in WATCHED_PATHS:
                    try:
                        val = cdb.get(read_sock, path)
                        print(f"  {path} = {val}")
                    except Exception as path_e:
                        print(f"  {path} -> Error: {path_e}")

        cdb.end_session(read_sock)
    finally:
        read_sock.close()


def read_configuration_values(paths: List[str]) -> None:
    """
    設定値を読み取って表示する

    Args:
        paths: 読み取り対象のパスリスト
    """
    # 読み取り専用セッションを開始
    read_sock = socket.socket()
    cdb.connect(read_sock, cdb.DATA_SOCKET, CONFD_HOST, CONFD_PORT)

    try:
        cdb.start_session(read_sock, cdb.RUNNING)

        print("--- Config Update Detected ---")
        for path in paths:
            try:
                val = cdb.get(read_sock, path)
                print(f"  {path} = {val}")
            except Exception as e:
                print(f"  {path} -> Error: {e}")

        cdb.end_session(read_sock)
    finally:
        read_sock.close()


def run_subscription_loop() -> None:
    """
    ConfDの設定変更を監視するメインループ

    設定変更が検知されると、変更された値を読み取って表示します。
    """
    # 購読用ソケットをセットアップ
    cdb_sock = socket.socket()
    cdb.connect(cdb_sock, cdb.DATA_SOCKET, CONFD_HOST, CONFD_PORT)

    # 監視対象パスを購読
    setup_subscription(cdb_sock, WATCHED_PATHS)

    print("Waiting for configuration changes...")

    try:
        while True:
            # 変更通知を待機(ブロッキング)
            cdb.read_subscription_socket(cdb_sock)

            # 変更された設定値を読み取る
            read_configuration_values(WATCHED_PATHS)

            # 設定の全文を取得
            read_full_configuration()

            # 通知処理の完了を報告(これがないと次の変更が届かない)
            cdb.sync_subscription_socket(cdb_sock, 1)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error in subscription loop: {e}")
        raise
    finally:
        cdb_sock.close()

# =============================================================================
# メイン関数
# =============================================================================

def main() -> None:
    """
    コマンドライン引数を解析してデーモンを制御する
    """
    parser = argparse.ArgumentParser(
        description='ConfD configuration change monitoring daemon',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start        Start the daemon
  %(prog)s --stop         Stop the daemon
  %(prog)s --status       Check daemon status
  %(prog)s --foreground   Run in foreground (for testing)
        """
    )

    parser.add_argument('--start', action='store_true', help='Start the daemon')
    parser.add_argument('--stop', action='store_true', help='Stop the daemon')
    parser.add_argument('--status', action='store_true', help='Check daemon status')
    parser.add_argument('--foreground', action='store_true', help='Run in foreground (for testing)')

    args = parser.parse_args()

    # コマンドを実行
    if args.start:
        start_daemon()
    elif args.stop:
        stop_daemon()
    elif args.status:
        status_daemon()
    elif args.foreground:
        print("Running in foreground mode (Ctrl-C to stop)")
        try:
            run_subscription_loop()
        except KeyboardInterrupt:
            print("\nStopped")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()