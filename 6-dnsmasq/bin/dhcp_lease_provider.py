#!/usr/bin/env python3
"""
DHCP リース状態プロバイダーデーモン

- YANG: dnsmasq-dhcp.yang (/dnsmasq/dhcp/leases)
- callpoint 名: dhcp_lease_cp （後で YANG augment か tailf:callpoint で設定）

dnsmasq のリースファイル(デフォルト: /var/lib/misc/dnsmasq.leases または
環境変数 DNSMASQ_LEASES_PATH)を読み取り、ConfD CLI から
"show dhcp leases" で閲覧できるようにします。
"""

import argparse
import atexit
import os
import select
import signal
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

try:
    import _confd  # type: ignore
    import _confd.dp as dp  # type: ignore
except ImportError as e:
    print(f"Error: Could not import required ConfD modules: {e}")
    sys.exit(1)

try:
    import dnsmasq_dhcp_ns as ns
except ImportError as e:
    print(f"Error: Could not import dnsmasq_dhcp_ns: {e}")
    sys.exit(1)

SCRIPT_BASE = Path(__file__).stem
SCRIPT_DIR = Path(__file__).resolve().parent.parent

TMP_DIR = SCRIPT_DIR / "tmp"
LOG_DIR = SCRIPT_DIR / "log"

PID_FILE = TMP_DIR / f"{SCRIPT_BASE}.pid"
LOG_FILE = LOG_DIR / f"{SCRIPT_BASE}.log"

CONFD_HOST = "127.0.0.1"
CONFD_PORT = 4565

CALLPOINT_NAME = "dhcp_lease_cp"
DAEMON_NAME = "dhcp_lease_provider_daemon"

# リースファイルパス
DEFAULT_LEASES_FILE = Path("/var/lib/misc/dnsmasq.leases")
LEASES_FILE = Path(os.environ.get("DNSMASQ_LEASES_PATH", str(DEFAULT_LEASES_FILE)))

# list lease のキー/葉のタグ(ハッシュ)は ns モジュールの dd_xxx を使用
IP_LEAF_TAG = ns.ns.dd_ip_address
MAC_LEAF_TAG = ns.ns.dd_mac
HOST_LEAF_TAG = ns.ns.dd_hostname
EXPIRY_LEAF_TAG = ns.ns.dd_expiry

wrksock_global: Optional[socket.socket] = None


class TransCallbacks:
    def cb_init(self, tctx) -> int:
        try:
            dp.trans_set_fd(tctx, wrksock_global)
            return _confd.OK
        except Exception as e:
            print(f"Transaction init failed: {e}")
            return _confd.ERR

    def cb_finish(self, tctx) -> int:
        return _confd.OK


class DataCallbacks:
    """Operational データ (/dnsmasq/dhcp/leases/lease) を提供するコールバック"""

    def cb_get_next(self, tctx, kp, pos) -> Tuple[int, Optional[Tuple[_confd.Value]]]:
        """list lease の走査用コールバック

        ConfD のリストコールバックパターンに従い、次のように動作します:
        - pos < 0 のとき: 最初の要素インデックス (0) とキー値を返す
        - pos >= 0 のとき: 次の要素インデックス (pos+1) とキー値を返す
        - 範囲外になったら _confd.NOK を返して終了
        """
        leases = _read_leases()
        if not leases:
            return _confd.NOK, None

        index = 0 if pos < 0 else pos + 1
        if index >= len(leases):
            return _confd.NOK, None

        ip, mac, hostname, expiry = leases[index]
        keyv = _confd.Value(ip, _confd.C_IPV4)
        return index, (keyv,)

    def cb_get_elem(self, tctx, kp) -> int:
        """指定ノード(leaf)の値を返す"""
        try:
            leases = _read_leases()
            if not leases:
                return 2  # NOT_FOUND

            # キー (ip-address) で対象エントリを特定
            key_ipv = kp[0][0]  # type: ignore[index]
            key_ip = str(key_ipv)

            target = None
            for ip, mac, hostname, expiry in leases:
                if ip == key_ip:
                    target = (ip, mac, hostname, expiry)
                    break

            if target is None:
                return 2

            ip, mac, hostname, expiry = target

            tag = kp.tag
            if tag == IP_LEAF_TAG:
                val = _confd.Value(ip, _confd.C_IPV4)
            elif tag == MAC_LEAF_TAG:
                val = _confd.Value(mac, _confd.C_STR)
            elif tag == HOST_LEAF_TAG:
                val = _confd.Value(hostname, _confd.C_STR)
            elif tag == EXPIRY_LEAF_TAG:
                val = _confd.Value(expiry, _confd.C_STR)
            else:
                return 2

            dp.data_reply_value(tctx, val)
            return _confd.OK
        except Exception as e:
            print(f"cb_get_elem failed: {e}")
            return _confd.ERR


def _read_leases() -> List[Tuple[str, str, str, str]]:
    """dnsmasq.leases を読み取り (ip, mac, hostname, expiry) のリストを返す"""
    leases: List[Tuple[str, str, str, str]] = []
    try:
        with open(LEASES_FILE, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 4:
                    continue
                expiry_epoch, mac, ip, hostname = parts[0:4]
                try:
                    expiry_dt = datetime.fromtimestamp(int(expiry_epoch))
                    expiry_str = expiry_dt.isoformat()
                except Exception:
                    expiry_str = expiry_epoch
                leases.append((ip, mac, hostname, expiry_str))
    except FileNotFoundError:
        # 実機 dnsmasq と連携していない場合など
        pass
    except Exception as e:
        print(f"Failed to read leases file {LEASES_FILE}: {e}")

    return leases


def daemonize() -> None:
    TMP_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #1 failed: {e}\n")
        sys.exit(1)

    os.chdir("/")
    os.setsid()
    os.umask(0)

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write(f"fork #2 failed: {e}\n")
        sys.exit(1)

    sys.stdout.flush()
    sys.stderr.flush()

    with open(str(LOG_FILE), "a") as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())

    with open(str(PID_FILE), "w") as f:
        f.write(str(os.getpid()))

    atexit.register(_cleanup_pid_file)


def _cleanup_pid_file() -> None:
    if PID_FILE.exists():
        PID_FILE.unlink()


def _get_pid() -> Optional[int]:
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None


def _is_running(pid: Optional[int]) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_daemon() -> None:
    pid = _get_pid()
    if _is_running(pid):
        print(f"dhcp_lease_provider is already running (PID: {pid})")
        sys.exit(1)

    _cleanup_pid_file()

    print("Starting dhcp_lease_provider daemon...")
    print(f"Log file: {LOG_FILE}")

    daemonize()
    run()


def stop_daemon() -> None:
    pid = _get_pid()
    if not _is_running(pid):
        print("dhcp_lease_provider is not running")
        _cleanup_pid_file()
        return

    print(f"Stopping dhcp_lease_provider (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            if not _is_running(pid):
                break
            signal.pause()
        if _is_running(pid):
            print("Forcing kill...")
            os.kill(pid, signal.SIGKILL)
    finally:
        _cleanup_pid_file()
        print("Stopped")


def status_daemon() -> None:
    pid = _get_pid()
    if _is_running(pid):
        print(f"dhcp_lease_provider is running (PID: {pid})")
        print(f"Log file: {LOG_FILE}")
    else:
        print("dhcp_lease_provider is not running")


def run() -> None:
    global wrksock_global

    print(f"Initializing daemon: {DAEMON_NAME}")
    dctx = dp.init_daemon(DAEMON_NAME)

    ctlsock = socket.socket()
    wrksock_global = socket.socket()

    dp.connect(dctx, ctlsock, dp.CONTROL_SOCKET, CONFD_HOST, CONFD_PORT)
    dp.connect(dctx, wrksock_global, dp.WORKER_SOCKET, CONFD_HOST, CONFD_PORT)

    trans_cb = TransCallbacks()
    data_cb = DataCallbacks()

    dp.register_trans_cb(dctx, trans_cb)
    dp.register_data_cb(dctx, CALLPOINT_NAME, data_cb)
    dp.register_done(dctx)

    stop_flag = {"stop": False}

    def signal_handler(signum, frame):
        print(f"Received signal {signum}, exiting...")
        stop_flag["stop"] = True

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    while not stop_flag["stop"]:
        rset = [ctlsock, wrksock_global]
        r, _, _ = select.select(rset, [], [], 1.0)
        if ctlsock in r:
            dp.fd_ready(dctx, ctlsock)
        if wrksock_global in r:
            dp.fd_ready(dctx, wrksock_global)

    dp.close(dctx)
    ctlsock.close()
    wrksock_global.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="DHCP lease provider daemon for ConfD")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--start", action="store_true", help="Daemonize and start")
    group.add_argument("--stop", action="store_true", help="Stop daemon")
    group.add_argument("--status", action="store_true", help="Show status")
    group.add_argument("--foreground", action="store_true", help="Run in foreground")
    args = parser.parse_args()

    if args.start:
        start_daemon()
    elif args.stop:
        stop_daemon()
    elif args.status:
        status_daemon()
    elif args.foreground:
        run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
