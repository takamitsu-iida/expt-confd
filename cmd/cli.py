#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple standalone CLI based on a small YANG model.

ConfD の Python API を一切使わず、以下を行う簡易 CLI を提供する:

* cmd/yang/example-cli.yang を読み込み、そこに定義された rpc 名を
    CLI のコマンドとして扱う
* 同じ YANG で定義した operational state (container state, config false)
    を ``show <leaf>`` で表示する
* prompt_toolkit を用いて、補完付きの対話的な CLI を実装する

このスクリプトは ConfD やその Python バインディングには依存しない。
YANG の解析には pyang を利用する。
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import importlib
import socket

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion

try:
    from pyang import context as yang_context
    from pyang import repository as yang_repository
except ImportError:  # pyang が無い場合は後でエラーメッセージを出す
    yang_context = None  # type: ignore[assignment]
    yang_repository = None  # type: ignore[assignment]


HERE = Path(__file__).resolve().parent
YANG_DIR = HERE / "yang"


@dataclass
class YangModel:
    """Very small subset of a YANG module needed for this demo.

    * rpc_names: 定義されている rpc 名一覧
    * rpc_descriptions: rpc ごとの description 文字列
    * rpc_handlers: rpc ごとの Python handler シンボル (module:function)
    * rpc_usages: rpc ごとの CLI usage 文字列
    * state_leaf_names: container state 配下の leaf 名一覧
    * state_leaf_descriptions: state leaf ごとの description 文字列
    * state_leaf_completions: state leaf ごとの補完候補 (オプション)
    * state_leaf_handlers: state leaf ごとの Python handler シンボル
    """

    rpc_names: List[str] = field(default_factory=list)
    state_leaf_names: List[str] = field(default_factory=list)
    rpc_descriptions: Dict[str, str] = field(default_factory=dict)
    state_leaf_descriptions: Dict[str, str] = field(default_factory=dict)
    state_leaf_completions: Dict[str, List[str]] = field(default_factory=dict)
    rpc_handlers: Dict[str, str] = field(default_factory=dict)
    rpc_usages: Dict[str, str] = field(default_factory=dict)
    state_leaf_handlers: Dict[str, str] = field(default_factory=dict)
    rpc_hidden: Dict[str, bool] = field(default_factory=dict)
    rpc_arg_styles: Dict[str, str] = field(default_factory=dict)


def load_example_yang(directory: Path) -> YangModel:
    """Load YANG modules in *directory* using pyang and collect metadata.

    - すべての rpc 名を収集
    - container state (config false) 以下の leaf 名を、入れ子も含めて収集

    pyang がインストールされていない場合は例外を投げる。
    """

    if yang_repository is None or yang_context is None:
        raise RuntimeError(
            "pyang is not available. Please install it in your environment.",
        )

    # ディレクトリ内の .yang ファイルをすべて対象にする
    yang_files = sorted(p for p in directory.glob("*.yang"))
    if not yang_files:
        raise FileNotFoundError(f"No YANG files found in {directory}")

    repo = yang_repository.FileRepository(str(directory))
    ctx = yang_context.Context(repo)

    modules = []
    for yf in yang_files:
        text = yf.read_text(encoding="utf-8")
        mod = ctx.add_module(yf.name, text)
        if mod is None:
            raise RuntimeError(f"Failed to parse YANG file: {yf}")
        modules.append(mod)

    # 構文木 (substmts) から必要な情報をたどる。
    model = YangModel()

    def _is_extension(stmt, localname: str) -> bool:
        """pyang の拡張ステートメント判定.

        keyword が "ex:cli-usage" のような文字列の場合と
        (prefix, localname) タプルの場合の両方を扱う。
        """

        key = getattr(stmt, "keyword", None)
        if isinstance(key, tuple) and len(key) == 2:
            return key[1] == localname
        if isinstance(key, str):
            return key.endswith(":" + localname) or key == localname
        return False

    def _first_description_arg(stmt) -> Optional[str]:
        for sub in getattr(stmt, "substmts", []) or []:
            if sub.keyword == "description" and isinstance(sub.arg, str):
                return sub.arg.strip()
        return None

    def _first_extension_arg(stmt, localname: str) -> Optional[str]:
        for sub in getattr(stmt, "substmts", []) or []:
            if isinstance(sub.arg, str) and _is_extension(sub, localname):
                return sub.arg.strip()
        return None

    def _has_extension(stmt, localname: str) -> bool:
        for sub in getattr(stmt, "substmts", []) or []:
            if _is_extension(sub, localname):
                return True
        return False

    def walk(stmt, in_state: bool) -> None:
        # rpc
        if stmt.keyword == "rpc":
            name = stmt.arg
            if name not in model.rpc_names:
                model.rpc_names.append(name)

            if name not in model.rpc_descriptions:
                desc = _first_description_arg(stmt)
                if desc is not None:
                    model.rpc_descriptions[name] = desc

            if name not in model.rpc_handlers:
                handler = _first_extension_arg(stmt, "python-handler")
                if handler is not None:
                    model.rpc_handlers[name] = handler

            if name not in model.rpc_usages:
                usage = _first_extension_arg(stmt, "cli-usage")
                if usage is not None:
                    model.rpc_usages[name] = usage

            if name not in model.rpc_arg_styles:
                style = _first_extension_arg(stmt, "rpc-arg-style")
                if style is not None:
                    model.rpc_arg_styles[name] = style

            # cli-hidden 拡張が付いていれば隠し RPC として扱う
            if name not in model.rpc_hidden and _has_extension(stmt, "cli-hidden"):
                model.rpc_hidden[name] = True

        # state コンテナ (config false)
        if stmt.keyword == "container":
            is_state_here = in_state
            if stmt.arg == "state":
                has_config_false = any(
                    sub.keyword == "config" and str(sub.arg) == "false"
                    for sub in stmt.substmts
                )
                if has_config_false:
                    is_state_here = True
            for sub in stmt.substmts:
                walk(sub, is_state_here)
            return

        # state コンテナ配下の leaf
        if in_state and stmt.keyword == "leaf":
            leaf_name = stmt.arg
            if leaf_name not in model.state_leaf_names:
                model.state_leaf_names.append(leaf_name)

            if leaf_name not in model.state_leaf_descriptions:
                desc = _first_description_arg(stmt)
                if desc is not None:
                    model.state_leaf_descriptions[leaf_name] = desc

            if leaf_name not in model.state_leaf_completions:
                comp = _first_extension_arg(stmt, "cli-completion")
                if comp is not None:
                    # 空白区切りの候補リストとみなす
                    model.state_leaf_completions[leaf_name] = comp.split()

            if leaf_name not in model.state_leaf_handlers:
                handler = _first_extension_arg(stmt, "state-python-handler")
                if handler is not None:
                    model.state_leaf_handlers[leaf_name] = handler

        for sub in getattr(stmt, "substmts", []) or []:
            walk(sub, in_state)

    for mod in modules:
        walk(mod, False)

    return model


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
        print("  exit, quit            - Exit the CLI")
        print("  help, ?               - Show this help")

        print("")
        print("Operational state (from YANG 'state' container):")
        for leaf in self.model.state_leaf_names:
            desc = self.model.state_leaf_descriptions.get(leaf, "")
            if desc:
                print(f"  {leaf:20s} - {desc}")
            else:
                print(f"  {leaf}")

        print("")
        print("RPC commands (from YANG):")
        for name in self.model.rpc_names:
            # cli-hidden な RPC は一般的なヘルプ一覧からは除外する
            if self.model.rpc_hidden.get(name):
                continue
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
            for leaf in self.model.state_leaf_names:
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

    def _rpc_ping(self, tokens: List[str]) -> None:
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
    # --- helper --------------------------------------------------------

    @staticmethod
    def _parse_key_value_args(tokens: List[str]) -> Optional[Dict[str, str]]:
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
        payload,
    ) -> None:
        """YANG で指定された Python handler を呼び出す。

        handler_symbol は 'module:function' 形式とする。

        payload の型は呼び出し元により異なる:
        - ping の場合:         List[str] (トークン列)
        - state leaf handler:  List[str] (leaf 以降のトークン列)
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
            "exit",
            "quit",
            "help",
            "?",
        ]
        # rpc 名はそのまま補完するが、cli-hidden なものは除外する
        commands.extend(
            name
            for name in self._cli.model.rpc_names
            if not self._cli.model.rpc_hidden.get(name)
        )

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
                    # "show <leaf> " の後は、leaf ごとの補完候補
                    leaf_name = tokens[1]
                    candidates = self._cli.model.state_leaf_completions.get(
                        leaf_name,
                        [],
                    )
                else:
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


def rpc_show_route(cli: "ExampleCli", args: Dict[str, str]) -> None:
    """YANG rpc show-route 用の Python ハンドラ。

    YANG では input leaf family を定義しているが、CLI からは
    "show route [ipv4|ipv6]" として呼び出される想定。

    - family が指定されなければ両方
    - family=ipv4 / ipv6 ならそのファミリのみ

    実際のルート出力は ExampleCli._show_route_state() に委譲する。
    """

    family = args.get("family") if args is not None else None
    if family not in {None, "ipv4", "ipv6"}:
        print("Usage: show route [ipv4|ipv6]")
        return

    cli._show_route_state(family)


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


def rpc_ping(cli: ExampleCli, tokens: List[str]) -> None:
    """YANG rpc 'ping' 用 handler."""

    cli._rpc_ping(tokens)


# --- state leaf 用ハンドラ -----------------------------------------------


def state_hostname(cli: ExampleCli, args: List[str]) -> None:
    """state leaf 'hostname' 用 handler."""

    value = cli.state.get("hostname")
    print(f"state hostname: {value}")


def state_mgmt_ip(cli: ExampleCli, args: List[str]) -> None:
    """state leaf 'mgmt-ip' 用 handler."""

    value = cli.state.get("mgmt-ip")
    print(f"state mgmt-ip: {value}")


def state_last_hello(cli: ExampleCli, args: List[str]) -> None:
    """state leaf 'last-hello' 用 handler."""

    value = cli.state.get("last-hello")
    print(f"state last-hello: {value}")


def state_last_add_result(cli: ExampleCli, args: List[str]) -> None:
    """state leaf 'last-add-result' 用 handler."""

    value = cli.state.get("last-add-result")
    print(f"state last-add-result: {value}")


def state_last_ping_target(cli: ExampleCli, args: List[str]) -> None:
    """state leaf 'last-ping-target' 用 handler."""

    value = cli.state.get("last-ping-target")
    print(f"state last-ping-target: {value}")


def state_last_ping_success(cli: ExampleCli, args: List[str]) -> None:
    """state leaf 'last-ping-success' 用 handler."""

    value = cli.state.get("last-ping-success")
    print(f"state last-ping-success: {value}")


def state_route(cli: ExampleCli, args: List[str]) -> None:
    """state leaf 'route' 用 handler.

    現状の CLI では "show route ..." は rpc show-route を通して
    実装しているため、このハンドラは実際には使われないが、
    YANG モデルの一貫性のために定義しておく。
    """

    # ルート情報の詳細表示は rpc_show_route/_show_route_state に任せる。
    summary = cli.state.get("route")
    print(f"state route: {summary}")


def main(argv: List[str]) -> int:
    # 将来的に複数 YANG を扱いたくなったときのために、ここで読み込み
    try:
        model = load_example_yang(YANG_DIR)
    except Exception as e:  # noqa: BLE001
        print(f"Failed to load YANG model: {e}", file=sys.stderr)
        return 1

    cli = ExampleCli(model)
    cli.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
