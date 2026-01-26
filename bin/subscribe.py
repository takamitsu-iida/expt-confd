#!/usr/bin/env python3

import socket
import _confd
import _confd.cdb as cdb
import sys
import os
import signal
import atexit
import argparse
from pathlib import Path

# PIDファイルのパス
PID_FILE = '/tmp/subscribe.pid'
# ログファイルのパス
LOG_FILE = '/tmp/subscribe.log'

def daemonize():
    """プロセスをデーモン化"""
    try:
        pid = os.fork()
        if pid > 0:
            # 親プロセスを終了
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #1 failed: {e}\n")
        sys.exit(1)

    # 親プロセスから切り離す
    os.chdir('/')
    os.setsid()
    os.umask(0)

    # 2回目のfork
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #2 failed: {e}\n")
        sys.exit(1)

    # 標準入出力をリダイレクト
    sys.stdout.flush()
    sys.stderr.flush()

    with open(LOG_FILE, 'a') as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())

    # PIDファイルを作成
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # 終了時にPIDファイルを削除
    atexit.register(lambda: os.remove(PID_FILE) if os.path.exists(PID_FILE) else None)

def get_pid():
    """PIDファイルからPIDを取得"""
    try:
        with open(PID_FILE, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None

def is_running(pid):
    """指定されたPIDのプロセスが実行中かチェック"""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def start_daemon():
    """デーモンを開始"""
    pid = get_pid()
    if is_running(pid):
        print(f"Subscribe daemon is already running (PID: {pid})")
        sys.exit(1)

    # 古いPIDファイルを削除
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    print("Starting subscribe daemon...")
    print(f"Log file: {LOG_FILE}")

    daemonize()
    run()

def stop_daemon():
    """デーモンを停止"""
    pid = get_pid()
    if not is_running(pid):
        print("Subscribe daemon is not running")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        sys.exit(1)

    print(f"Stopping subscribe daemon (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        # プロセスが終了するまで待つ
        import time
        for _ in range(10):
            if not is_running(pid):
                break
            time.sleep(0.5)

        if is_running(pid):
            print("Daemon did not stop gracefully, forcing...")
            os.kill(pid, signal.SIGKILL)

        print("Daemon stopped")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception as e:
        print(f"Error stopping daemon: {e}")
        sys.exit(1)

def status_daemon():
    """デーモンのステータスを表示"""
    pid = get_pid()
    if is_running(pid):
        print(f"Subscribe daemon is running (PID: {pid})")
        print(f"Log file: {LOG_FILE}")
    else:
        print("Subscribe daemon is not running")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

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
    except Exception as e:
        print(f"Error: {e}")
        cdb_sock.close()
        raise

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='ConfD subscription daemon')
    parser.add_argument('--start', action='store_true', help='Start the daemon')
    parser.add_argument('--stop', action='store_true', help='Stop the daemon')
    parser.add_argument('--status', action='store_true', help='Check daemon status')
    parser.add_argument('--foreground', action='store_true', help='Run in foreground (for testing)')

    args = parser.parse_args()

    if args.start:
        start_daemon()
    elif args.stop:
        stop_daemon()
    elif args.status:
        status_daemon()
    elif args.foreground:
        print("Running in foreground mode...")
        run()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()