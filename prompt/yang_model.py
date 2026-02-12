from __future__ import annotations

"""YANG モデルの最小表現と読み込み処理を提供するモジュール。"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    from pyang import context as yang_context
    from pyang import repository as yang_repository
except ImportError:  # pyang が無い場合は後でエラーメッセージを出す
    yang_context = None  # type: ignore[assignment]
    yang_repository = None  # type: ignore[assignment]


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
    * rpc_arg_styles: rpc 引数スタイル ("kv" / "positional" など)
    * rpc_input_params: rpc の input セクションで定義された leaf 名一覧
    """

    rpc_names: List[str] = field(default_factory=list)
    state_leaf_names: List[str] = field(default_factory=list)
    rpc_descriptions: Dict[str, str] = field(default_factory=dict)
    state_leaf_descriptions: Dict[str, str] = field(default_factory=dict)
    state_leaf_completions: Dict[str, List[str]] = field(default_factory=dict)
    rpc_handlers: Dict[str, str] = field(default_factory=dict)
    rpc_usages: Dict[str, str] = field(default_factory=dict)
    state_leaf_handlers: Dict[str, str] = field(default_factory=dict)
    rpc_arg_styles: Dict[str, str] = field(default_factory=dict)
    rpc_input_params: Dict[str, List[str]] = field(default_factory=dict)


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

    def _collect_input_leaf_names(input_stmt) -> List[str]:
        """Recursively collect leaf names under an rpc's input statement."""

        names: List[str] = []

        def _walk_input(s) -> None:
            if s.keyword == "leaf":
                if isinstance(s.arg, str) and s.arg not in names:
                    names.append(s.arg)
            for child in getattr(s, "substmts", []) or []:
                _walk_input(child)

        _walk_input(input_stmt)
        return names

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

            # rpc input セクションから引数 leaf 名を収集しておく
            if name not in model.rpc_input_params:
                for sub in getattr(stmt, "substmts", []) or []:
                    if sub.keyword == "input":
                        params = _collect_input_leaf_names(sub)
                        if params:
                            model.rpc_input_params[name] = params
                        break

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
