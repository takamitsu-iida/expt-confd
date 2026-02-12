from __future__ import annotations

"""Example YANG CLI 本体と補完、各種ハンドラ群を集約したモジュール。"""

import importlib
import shlex
import socket
import subprocess
from typing import Dict, List, Optional, Sequence, Union

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion

from yang_model import YangModel


class ExampleCli:
    """prompt_toolkit ベースの対話 CLI 本体。"""

    intro = "Example YANG CLI. Type 'help' or '?' for help."
    prompt = "ex> "

    def __init__(self, model: YangModel) -> None:
        self.model = model
        self.session = PromptSession()

        # 非永続な簡易 state 形
        # YANGのstate leafから生成する。
        self.state: Dict[str, Optional[str]] = {
            leaf: None for leaf in self.model.state_leaf_names
        }

        # いくつかのよくある項目だけ、存在すればデフォルト値を与える。
        if "hostname" in self.state:
            self.state["hostname"] = socket.gethostname()

        if "mgmt-ip" in self.state:
            # demo 用の固定値 (必要なら YANG 側に default を追加してもよい)
            self.state["mgmt-ip"] = "192.0.2.1"

        if "route" in self.state:
            # route は詳細表示用サマリ
            self.state["route"] = "use 'show route [ipv4|ipv6]'"

    def run(self) -> None:
        """メインの REPL ループを実行する。"""

        print(self.intro)
        completer = CliCompleter(self)
        while True:
            try:
                line = self.session.prompt(self.prompt, completer=completer)
            except EOFError:
                # Ctrl-D で終了
                print()
                break
            except KeyboardInterrupt:
                # Ctrl-C では行をキャンセルして再度プロンプト
                print()
                continue

            line = line.strip()
            if not line:
                # 空行では何もしない
                continue

            if not self._handle_line(line):
                break

    def _handle_line(self, line: str) -> bool:
        """1 行分の入力を処理する。

        戻り値が False の場合、REPL を終了する。
        """

        # 組み込み bash サブシェル起動
        # "bash" と入力すると /usr/bin/bash を起動し、終了後に CLI に戻る。
        if line == "bash":
            self._run_bash_shell()
            return True

        # 終了系
        if line in {"exit", "quit"}:
            return False

        if line in {"help", "?"}:
            self._print_help()
            return True

        # 以降はトークン単位で処理する
        try:
            tokens = shlex.split(line)
        except ValueError as e:
            print(f"parse error: {e}")
            return True

        if not tokens:
            return True

        # show 系コマンド
        if tokens[0] == "show":
            # 2語目以降が無い場合は使い方を案内
            if len(tokens) == 1:
                print("Usage: show <leaf> [<args>]")
                return True

            # show state ... はサポートしない (古い書き方を明示的に拒否)
            if tokens[1] == "state":
                print("Do not use 'state'. Use: show <leaf> [...]")
                return True

            # show <leaf> [...] を内部的に
            # "state <leaf> [...]" にマップ
            # 例: show hostname -> "state hostname"
            arg = "state " + " ".join(tokens[1:])

            self.do_show(arg)
            return True

        name = tokens[0]
        if name not in self.model.rpc_names:
            print(f"Unknown command: {name}")
            return True

        # "<rpc> help" / "<rpc> ?" でその RPC の usage を表示
        if len(tokens) == 2 and tokens[1] in {"help", "?"}:
            usage = self.model.rpc_usages.get(name) or name
            desc = self.model.rpc_descriptions.get(name, "")
            if desc:
                print(usage)
                print(f"  {desc}")
            else:
                print(usage)
            return True

        # YANG で指定された Python handler を優先的に使う
        handler_symbol = self.model.rpc_handlers.get(name)

        # 引数スタイルは YANG の rpc-arg-style から取得 (デフォルトは kv)
        arg_style = self.model.rpc_arg_styles.get(name, "kv")

        if arg_style == "positional":
            payload = tokens[1:]
            if handler_symbol:
                self._dispatch_handler(handler_symbol, name, payload)
            else:
                # 後方互換: 既存のハードコード実装を使用
                if name == "ping":
                    self._rpc_ping(payload)
                else:
                    print(f"rpc '{name}' (positional) has no handler.")
            return True

        # デフォルトは key=value 形式でパース
        args = self._parse_key_value_args(tokens[1:])
        if args is None:
            return True

        if handler_symbol:
            self._dispatch_handler(handler_symbol, name, args)
        else:
            # 後方互換: 既存のハードコード実装を使用
            if name == "hello":
                self._rpc_hello(args)
            elif name == "add":
                self._rpc_add(args)
            elif name == "set-hostname":
                self._rpc_set_hostname(args)
            else:
                print(f"rpc '{name}' is defined in YANG but not implemented.")

        return True

    def _print_help(self) -> None:
        """YANG モデルから生成した簡単なヘルプを表示する。"""

        print("Available built-in commands:")
        print("  show <leaf> [<args>]  - Show operational state")
        print("  bash                  - Start /usr/bin/bash shell")
        print("  exit, quit            - Exit the CLI")
        print("  help, ?               - Show this help")

        print("")
        print("RPC commands (from YANG):")
        for name in sorted(self.model.rpc_names):
            desc = self.model.rpc_descriptions.get(name, "")
            # usage は YANG の cli-usage 拡張から取得
            usage = self.model.rpc_usages.get(name)
            if not usage:
                # usage が未指定な場合のフォールバック
                usage = name

            if desc:
                print(f"  {usage:24s} - {desc}")
            else:
                print(f"  {usage}")

    # --- show コマンド -------------------------------------------------

    def do_show(self, arg: str) -> None:
        """show <leaf> [<args>]

        YANG の container state に対応する operational state を表示する。
        """

        try:
            tokens = shlex.split(arg)
        except ValueError as e:  # 不正なクオートなど
            print(f"parse error: {e}")
            return

        if not tokens:
            print("Usage: show <leaf> [<args>]")
            return

        if tokens[0] != "state":
            # 内部的には常に "state ..." で呼ばれる想定
            print("Internal error: unexpected show argument")
            return

        # すべての leaf を表示
        if len(tokens) == 1:
            print("state:")
            for leaf in sorted(self.model.state_leaf_names):
                value = self.state.get(leaf)
                print(f"  {leaf}: {value}")
            return

        # 通常の 1 レベル leaf 表示
        leaf = tokens[1]
        if leaf not in self.model.state_leaf_names:
            print(f"Unknown state leaf: {leaf}")
            return

        # YANG で state leaf 用の Python handler が定義されていれば、
        # それを優先的に呼び出す。payload には leaf 以降のトークンを
        # そのまま渡す (位置引数スタイル)。
        handler_symbol = self.model.state_leaf_handlers.get(leaf)
        if handler_symbol:
            extra_tokens = tokens[2:]
            self._dispatch_handler(handler_symbol, f"state-{leaf}", extra_tokens)
            return

        # ハンドラが無い場合のフォールバック: 単純に state dict を表示
        value = self.state.get(leaf)
        print(f"state {leaf}: {value}")

    # --- rpc 実装 ------------------------------------------------------

    def _rpc_hello(self, args: Dict[str, str]) -> None:
        """Demo implementation of rpc hello.

        主に ExampleCli 内部から呼ばれる実装。YANG からは
        rpc_hello() ラッパー経由で利用される。
        """

        name = args.get("name", "world")
        greeting = f"Hello, {name}!"
        # YANG の output に対応する値を表示
        print(f"greeting={greeting}")
        # state を更新
        self.state["last-hello"] = greeting

    def _rpc_add(self, args: Dict[str, str]) -> None:
        try:
            x = int(args.get("x", "0"))
            y = int(args.get("y", "0"))
        except ValueError:
            print("x と y は整数で指定してください (例: add x=1 y=2)")
            return

        result = x + y
        print(f"result={result}")
        self.state["last-add-result"] = str(result)

    def _rpc_set_hostname(self, args: Dict[str, str]) -> None:
        """Demo implementation of rpc set-hostname.

        実際の OS のホスト名は変更せず、内部 state だけを書き換える。
        """

        hostname = args.get("hostname")
        if not hostname:
            print("Usage: set-hostname hostname=<name>")
            return

        self.state["hostname"] = hostname
        print(f"result=hostname set to '{hostname}'")

    def _rpc_ping(self, tokens: Sequence[str]) -> None:
        """Implementation of rpc ping.

        実際の OS の `ping` コマンドを呼び出し、その成否を state に反映する。
        CLI からは次のように呼び出す:

          ping <destination> [count]
        """

        if not tokens:
            print("Usage: ping <destination> [count]")
            return

        dest = tokens[0]
        count = 4
        if len(tokens) >= 2:
            try:
                count = int(tokens[1])
            except ValueError:
                print("count は整数で指定してください (例: ping 1.1.1.1 3)")
                return

        print(f"PING {dest} with {count} packets (system ping)...")

        # システムの ping コマンドを使って簡易に成否だけ確認する
        try:
            completed = subprocess.run(
                ["ping", "-c", str(count), dest],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            success = completed.returncode == 0
        except FileNotFoundError:
            print("system 'ping' command not found; treating as success for demo.")
            success = True
        except KeyboardInterrupt:
            # ユーザが Ctrl-C で ping を中断した場合
            print("\nPing aborted by user.")
            self.state["last-ping-target"] = dest
            self.state["last-ping-success"] = "false"
            return

        print(f"success={'true' if success else 'false'}")

        self.state["last-ping-target"] = dest
        self.state["last-ping-success"] = "true" if success else "false"

    def _show_route_state(self, family: Optional[str]) -> None:
        """Show routing state for `show route [...]`."""

        # Demo 用のダミー経路データ
        ipv4_routes = [
            ("0.0.0.0/0", "192.0.2.254", 1),
            ("192.0.2.0/24", "0.0.0.0", 0),
        ]
        ipv6_routes = [
            ("::/0", "2001:db8::ffff", 1),
            ("2001:db8::/64", "::", 0),
        ]

        def print_ipv4() -> None:
            print("state route ipv4:")
            for prefix, nexthop, metric in ipv4_routes:
                print(f"  {prefix:18s} via {nexthop:15s} metric {metric}")

        def print_ipv6() -> None:
            print("state route ipv6:")
            for prefix, nexthop, metric in ipv6_routes:
                print(f"  {prefix:24s} via {nexthop:20s} metric {metric}")

        if family is None:
            print_ipv4()
            print("")
            print_ipv6()
        elif family == "ipv4":
            print_ipv4()
        else:  # ipv6
            print_ipv6()

    def _run_bash_shell(self) -> None:
        """/usr/bin/bash を起動し、終了するまで待つ。"""

        try:
            # 現在の端末をそのまま使って bash を起動する。
            # bash を抜けると CLI のプロンプトに戻る。
            subprocess.run(["/usr/bin/bash"])
        except FileNotFoundError:
            print("/usr/bin/bash not found.")
        except KeyboardInterrupt:
            # bash 実行中の Ctrl-C はここまで伝播しないはずだが、念のため
            print("\nInterrupted while running bash shell.")

    # --- helper --------------------------------------------------------

    @staticmethod
    def _parse_key_value_args(tokens: Sequence[str]) -> Optional[Dict[str, str]]:
        """Parse ['k1=v1', 'k2=v2', ...] into a dict.

        フォーマットが不正な場合はメッセージを表示して None を返す。
        """

        result: Dict[str, str] = {}
        for t in tokens:
            if "=" not in t:
                print(f"Invalid argument (expected key=value): {t}")
                return None
            k, v = t.split("=", 1)
            if not k:
                print(f"Invalid argument (empty key): {t}")
                return None
            result[k] = v
        return result

    def _dispatch_handler(
        self,
        handler_symbol: str,
        rpc_name: str,
        payload: Union[Dict[str, str], Sequence[str]],
    ) -> None:
        """YANG で指定された Python handler を呼び出す。

        handler_symbol は 'module:function' 形式とする。

        payload の型は呼び出し元により異なる:
        - ping の場合:         Sequence[str] (トークン列)
        - state leaf handler:  Sequence[str] (leaf 以降のトークン列)
        - それ以外の rpc:      Dict[str, str] (key=value でパース済み)
        """

        try:
            module_name, func_name = handler_symbol.split(":", 1)
        except ValueError:
            print(f"Invalid handler symbol for rpc '{rpc_name}': {handler_symbol}")
            return

        try:
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
        except Exception as e:  # noqa: BLE001
            print(f"Failed to load handler for rpc '{rpc_name}': {e}")
            return

        # ハンドラには (cli, payload) を渡す契約とする
        try:
            func(self, payload)
        except Exception as e:  # noqa: BLE001
            print(f"Error while executing handler for rpc '{rpc_name}': {e}")


class CliCompleter(Completer):
    """prompt_toolkit 用のシンプルな補完クラス。"""

    def __init__(self, cli: ExampleCli) -> None:
        self._cli = cli

    # type: ignore[override]
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        # シェル風の分割を行う。末尾が空白なら空トークンを追加しておく。
        try:
            tokens = shlex.split(text)
        except ValueError:
            return

        if text.endswith(" "):
            tokens.append("")

        word = document.get_word_before_cursor(WORD=True) or ""

        # トップレベルの候補
        commands = [
            "show",
            "bash",
            "exit",
            "quit",
            "help",
            "?",
        ]
        # rpc 名はそのまま補完する
        commands.extend(self._cli.model.rpc_names)

        # 文脈に応じた候補を決める
        candidates: List[str]
        if not tokens or len(tokens) == 1:
            # 1語目の補完
            candidates = commands
        elif tokens[0] == "show":
            if len(tokens) == 2:
                # "show " の直後は state leaf 名をそのまま補完
                candidates = self._cli.model.state_leaf_names
            else:
                # "show <leaf> ..." 形式の場合
                if len(tokens) >= 3:
                    leaf_name = tokens[1]
                    base = self._cli.model.state_leaf_completions.get(
                        leaf_name,
                        [],
                    )
                    # leaf 名の後に「非空トークン + 末尾の空トークン」があれば、
                    # すなわち "show route ipv4 " のように完全に入力済みとみなし、
                    # <CR> のみを候補に出す。それ以外 (例: "show route i") では
                    # 通常どおり base を使い、word プレフィックスでフィルタする。
                    tail = tokens[2:]
                    has_non_empty = any(t for t in tail)
                    ends_with_empty = bool(tail) and tail[-1] == ""
                    if has_non_empty and ends_with_empty:
                        candidates = [c for c in base if c == "<CR>"]
                    else:
                        candidates = base
                else:
                    candidates = []
        elif tokens[0] in self._cli.model.rpc_names:
            # rpc 名の後ろでの補完 (kv スタイル向け)
            rpc_name = tokens[0]
            arg_style = self._cli.model.rpc_arg_styles.get(rpc_name, "kv")
            if arg_style != "positional":
                # YANG input から収集した leaf 名を key= 形式で提案する
                param_names = self._cli.model.rpc_input_params.get(rpc_name, [])

                # すでに指定済みの key は候補から除外する
                used_keys = set()
                # 末尾の空トークン (入力中) は除外してチェックする
                check_tokens = tokens[1:-1] if tokens and tokens[-1] == "" else tokens[1:]
                for t in check_tokens:
                    if "=" in t:
                        k, _ = t.split("=", 1)
                        if k:
                            used_keys.add(k)

                base = [f"{name}=" for name in param_names if name not in used_keys]
                candidates = base
            else:
                # 位置引数スタイルの rpc では特に補完しない
                candidates = []
        else:
            # それ以外は特に文脈依存補完はしない
            candidates = []

        for c in candidates:
            if not word or c.startswith(word):
                # 特別な sentinel "<CR>" は「そのまま Enter」であることを
                # 示すために表示だけ行い、実際には何も挿入しない。
                if c == "<CR>":
                    yield Completion("", start_position=-len(word), display="<CR>")
                else:
                    yield Completion(c, start_position=-len(word))


# --- YANG から指定される Python handler 用ラッパー ------------------------
#
# YANG モジュール側では "python-handler" / "state-python-handler" 拡張に
# "module:function" 形式でシンボル名を記述する。そのため、ExampleCli
# の内部メソッドを直接指定するのではなく、ここで薄いラッパー関数を
# 定義して公開している。


def rpc_hello(cli: ExampleCli, args: Dict[str, str]) -> None:
    """YANG rpc 'hello' 用 handler.

    ExampleCli の内部メソッドに委譲する。
    """

    cli._rpc_hello(args)


def rpc_add(cli: ExampleCli, args: Dict[str, str]) -> None:
    """YANG rpc 'add' 用 handler."""

    cli._rpc_add(args)


def rpc_set_hostname(cli: ExampleCli, args: Dict[str, str]) -> None:
    """YANG rpc 'set-hostname' 用 handler."""

    cli._rpc_set_hostname(args)


def rpc_ping(cli: ExampleCli, tokens: Sequence[str]) -> None:
    """YANG rpc 'ping' 用 handler."""

    cli._rpc_ping(tokens)


# --- state leaf 用ハンドラ -----------------------------------------------


def state_hostname(cli: ExampleCli, _args: Sequence[str]) -> None:
    """state leaf 'hostname' 用 handler."""

    value = cli.state.get("hostname")
    print(f"state hostname: {value}")


def state_mgmt_ip(cli: ExampleCli, _args: Sequence[str]) -> None:
    """state leaf 'mgmt-ip' 用 handler."""

    value = cli.state.get("mgmt-ip")
    print(f"state mgmt-ip: {value}")


def state_last_hello(cli: ExampleCli, _args: Sequence[str]) -> None:
    """state leaf 'last-hello' 用 handler."""

    value = cli.state.get("last-hello")
    print(f"state last-hello: {value}")


def state_last_add_result(cli: ExampleCli, _args: Sequence[str]) -> None:
    """state leaf 'last-add-result' 用 handler."""

    value = cli.state.get("last-add-result")
    print(f"state last-add-result: {value}")


def state_last_ping_target(cli: ExampleCli, _args: Sequence[str]) -> None:
    """state leaf 'last-ping-target' 用 handler."""

    value = cli.state.get("last-ping-target")
    print(f"state last-ping-target: {value}")


def state_last_ping_success(cli: ExampleCli, _args: Sequence[str]) -> None:
    """state leaf 'last-ping-success' 用 handler."""

    value = cli.state.get("last-ping-success")
    print(f"state last-ping-success: {value}")


def state_route(cli: ExampleCli, args: Sequence[str]) -> None:
    """state leaf 'route' 用 handler.

    "show route [ipv4|ipv6]" を state ベースで実装する。
    """

    # args には "show route" 以降のトークンが入っている想定
    family: Optional[str] = None
    if len(args) == 0:
        family = None
    elif len(args) == 1:
        family = args[0]
    else:
        print("Usage: show route [ipv4|ipv6]")
        return

    if family not in {None, "ipv4", "ipv6"}:
        print("Usage: show route [ipv4|ipv6]")
        return

    cli._show_route_state(family)
