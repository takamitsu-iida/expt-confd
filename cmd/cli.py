#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple standalone CLI based on a small YANG model.

ConfD の Python API を一切使わず、以下を行う簡易 CLI を提供する:

* cmd/yang/example-cli.yang を読み込み、そこに定義された rpc 名を
        CLI のコマンドとして扱う
* 同じ YANG で定義した operational state (container state, config false)
        を ``show state`` / ``show state <leaf>`` で表示する
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
    """

    rpc_names: List[str] = field(default_factory=list)
    state_leaf_names: List[str] = field(default_factory=list)
    rpc_descriptions: Dict[str, str] = field(default_factory=dict)
    state_leaf_descriptions: Dict[str, str] = field(default_factory=dict)
    rpc_handlers: Dict[str, str] = field(default_factory=dict)
    rpc_usages: Dict[str, str] = field(default_factory=dict)


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

        # show コマンド
        if line.startswith("show"):
            parts = line.split(maxsplit=1)
            arg = parts[1] if len(parts) == 2 else ""
            self.do_show(arg)
            return True

        # それ以外は rpc として扱う
        try:
            tokens = shlex.split(line)
        except ValueError as e:
            print(f"parse error: {e}")
            return True

        if not tokens:
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

        # ping だけは空白区切り引数
        if name == "ping":
            if handler_symbol:
                self._dispatch_handler(handler_symbol, name, tokens[1:])
            else:
                # 後方互換用のフォールバック
                self._rpc_ping(tokens[1:])
            return True

        # それ以外は key=value 形式でパース
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
        print("  show state [<leaf>]   - Show operational state")
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
        """show state [<leaf>]

        YANG の container state に対応する operational state を表示する。
        """

        try:
            tokens = shlex.split(arg)
        except ValueError as e:  # 不正なクオートなど
            print(f"parse error: {e}")
            return

        if not tokens:
            print("Usage: show state [<leaf>]")
            return

        if tokens[0] != "state":
            print("Only 'show state' is supported in this demo.")
            return

        if len(tokens) == 1:
            # すべての leaf
            print("state:")
            for leaf in self.model.state_leaf_names:
                value = self.state.get(leaf)
                print(f"  {leaf}: {value}")
            return

        leaf = tokens[1]
        if leaf not in self.model.state_leaf_names:
            print(f"Unknown state leaf: {leaf}")
            return

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
        - ping の場合: payload は List[str] (トークン列)
        - それ以外:   payload は Dict[str, str] (key=value でパース済み)
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
        commands.extend(self._cli.model.rpc_names)

        # 文脈に応じた候補を決める
        candidates: List[str]
        if not tokens or len(tokens) == 1:
            # 1語目の補完
            candidates = commands
        elif tokens[0] == "show":
            if len(tokens) == 2:
                # "show " の直後は state
                candidates = ["state"]
            elif len(tokens) == 3 and tokens[1] == "state":
                # "show state " の後は state leaf 名
                candidates = self._cli.model.state_leaf_names
            else:
                candidates = []
        else:
            # それ以外は特に文脈依存補完はしない
            candidates = []

        for c in candidates:
            if not word or c.startswith(word):
                yield Completion(c, start_position=-len(word))


# --- YANG から指定される Python handler 用ラッパー ------------------------


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
