#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple standalone CLI based on a small YANG model.

ConfD の Python API を一切使わず、以下を行う簡易 CLI を提供する:

* yang/example-cli.yang を読み込み、そこに定義された rpc 名をCLI のコマンドとして扱う
* 同じ YANG で定義した operational state (container state, config false)を ``show <leaf>`` で表示する
* prompt_toolkit を用いて、補完付きの対話的な CLI を実装する

このファイルは CLI のエントリポイントのみを提供し、YANG モデルの
読み込みロジックは yang_model モジュールに、CLI 本体とハンドラ類は
cli_core モジュールに分離している。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from cli_core import ExampleCli
from yang_model import load_example_yang


HERE = Path(__file__).resolve().parent
YANG_DIR = HERE / "yang"


def main(argv: List[str]) -> int:
    """CLI エントリポイント関数。

    現時点では *argv* は使用していないが、将来的にコマンドライン
    オプションを追加する際の拡張余地として受け取っている。
    """

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
