#!/bin/bash

# ----------------------------------------------------------------------
# setup.sh
#   - 依存ツール (python, pip, direnv) のインストール
#   - 設定ファイルテンプレートのコピー
#   - Python依存性のインストール、
#   - 設定ファイル生成
# ----------------------------------------------------------------------

# このスクリプトが格納されているディレクトリの絶対パスを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# プロジェクトのルートディレクトリを特定 (setup.shがbinディレクトリにあると仮定)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 実行ディレクトリをプロジェクトルートに移動
cd "$PROJECT_ROOT" || { echo "エラー: プロジェクトルート $PROJECT_ROOT に移動できませんでした。" >&2; exit 1; }

# スクリプトと設定ファイルのパスを定義
SETUP_CONFIG_SCRIPT="$SCRIPT_DIR/setup.py"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
ENVRC_FILE="$PROJECT_ROOT/.envrc"
ENVRC_SAMPLE_FILE="$PROJECT_ROOT/.envrc.sample"

echo ""
echo "----------------------------------------------------"
echo "セットアップを開始します。"
echo "このスクリプトは必要な開発ツールをシステムにインストールするため、"
echo "管理者権限 (sudo) を必要とすることがあります。"
echo "----------------------------------------------------"
echo ""

# 必要なパッケージをインストールする関数
install_tools() {
    local packages_to_install=()
    local install_cmd=""

    if ! command -v python3 >/dev/null; then
        packages_to_install+=(python3)
    fi

    if ! command -v direnv >/dev/null; then
        packages_to_install+=(direnv)
    fi

    if ! command -v make >/dev/null; then
        packages_to_install+=(make)
    fi

    if [ ${#packages_to_install[@]} -eq 0 ] && command -v pip3 >/dev/null; then
        echo "python3, pip3, direnv, makeは既にインストールされています。スキップします。"
        return 0
    fi

    echo "不足している開発ツール (${packages_to_install[*]}) のインストールを開始します..."

    # Debian/Ubuntu (apt)
    if command -v apt >/dev/null; then
        echo "--> Debian/Ubuntu環境を検出"
        sudo apt update
        install_cmd="sudo apt install -y python3 python3-pip python3-venv direnv make"

    # RHEL/Fedora/CentOS (dnf/yum)
    elif command -v dnf >/dev/null; then
        echo "--> RHEL/Fedora/CentOS環境 (dnf) を検出"
        install_cmd="sudo dnf install -y python3 python3-pip python3-venv direnv make"

    elif command -v yum >/dev/null; then
        echo "--> CentOS環境 (yum) を検出"
        install_cmd="sudo yum install -y python3 python3-pip python3-venv direnv make"

    # openSUSE/SUSE (zypper)
    elif command -v zypper >/dev/null; then
        echo "--> openSUSE/SUSE環境を検出"
        install_cmd="sudo zypper install -y python3 python3-pip python3-venv direnv make"

    else
        echo "⚠️ 互換性のあるパッケージマネージャーが見つかりませんでした。"
        echo "python3, python3-pip, direnv, makeを手動でインストールしてください。"
        exit 1
    fi

    if [ -n "$install_cmd" ]; then
        eval "$install_cmd"
        if [ $? -ne 0 ]; then
            echo "❌ 開発ツールのインストール中にエラーが発生しました。"
            exit 1
        fi
    fi
}


# direnvをシェルにフックする関数
setup_direnv_hook() {
    local hook_line='eval "$(direnv hook bash)"'
    local rc_file=""

    if [ -n "$BASH_VERSION" ] && [ -f "$HOME/.bashrc" ]; then
        rc_file="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ] && [ -f "$HOME/.zshrc" ]; then
        rc_file="$HOME/.zshrc"
    else
        echo "⚠️ direnvのフックを自動で設定できませんでした。"
        echo "手動でシェル設定ファイル (.bashrcまたは.zshrc) に以下を追記してください:"
        echo "    $ hook_line"
        return
    fi

    if ! grep -q "$hook_line" "$rc_file"; then
        echo "" >> "$rc_file"
        echo "$hook_line" >> "$rc_file"
        echo "✅ direnvフックを $rc_file に追記しました。"
        echo "変更を有効にするため、このターミナルセッションを再起動するか、"
        echo " 'source $rc_file' を実行してください。"
    else
        echo "✅ direnvフックは $rc_file に既に設定されています。"
    fi
}

# direnvの設定ファイル（.envrc）を処理する関数
setup_envrc() {
    if [ -f "$ENVRC_FILE" ]; then
        echo "⚠️ $ENVRC_FILE が既に存在します。上書きを避けるため、スキップします。"

    elif [ -f "$ENVRC_SAMPLE_FILE" ]; then
        echo "--- $ENVRC_SAMPLE_FILE を $ENVRC_FILE としてコピーします ---"
        cp "$ENVRC_SAMPLE_FILE" "$ENVRC_FILE"
        echo "✅ $ENVRC_FILE ファイルを生成しました。"

    else
        echo "❌ $ENVRC_FILE も $ENVRC_SAMPLE_FILE も見つかりません。direnvの設定をスキップします。"
        echo "プロジェクトのPython仮想環境を使用するには、手動で .envrc を作成してください。"
        return
    fi

    if command -v direnv >/dev/null && [ -f "$ENVRC_FILE" ]; then
        echo "--- direnvにこのディレクトリを信頼させます ---"
        direnv allow .
    fi
}

# 設定ファイルテンプレートをコピーする関数
copy_config_file() {
    local sample_file="$1"
    local dest_file="$2"

    if [ -f "$dest_file" ]; then
        echo "⚠️ 設定ファイル $dest_file は既に存在します。上書きを避けるためスキップしました。"
    elif [ -f "$sample_file" ]; then
        echo "--- $sample_file を $dest_file としてコピーします ---"
        cp "$sample_file" "$dest_file"
        echo "✅ 設定ファイル $dest_file を生成しました。"
    else
        echo "❌ テンプレート $sample_file が見つかりません。コピーをスキップしました。"
    fi
}

# Pythonの依存関係をインストールする関数
install_python_deps() {
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        echo "⚠️ $REQUIREMENTS_FILE が見つかりません。Python依存性のインストールをスキップします。"
        return 0
    fi

    # .envrcが存在し、direnvが利用可能な場合は、direnvで環境変数をロード
    if [ -f "$ENVRC_FILE" ] && command -v direnv >/dev/null; then
        echo "--- direnvで環境変数をロード中 ---"
        eval "$(direnv export bash)"
    fi

    # 仮想環境が有効でない場合は作成してアクティベート
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ ! -d ".venv" ]; then
            echo "--- 仮想環境 (.venv) を作成します ---"
            python3 -m venv .venv
        fi
        echo "--- 仮想環境をアクティベート中 ---"
        source .venv/bin/activate
    else
        echo "✅ 仮想環境は既にアクティベートされています: $VIRTUAL_ENV"
    fi

    echo "--- pipを最新バージョンにアップグレード中 ---"
    python3 -m pip install --upgrade pip

    echo "--- requirements.txtからPythonモジュールをインストール中 ---"
    python3 -m pip install -r "$REQUIREMENTS_FILE"

    if [ $? -ne 0 ]; then
        echo "❌ Python依存性のインストール中にエラーが発生しました。"
        return 1
    fi

    return 0
}

# 設定ファイル生成スクリプトを実行する関数
run_config_script() {
    if [ ! -f "$SETUP_CONFIG_SCRIPT" ]; then
        echo "❌ $SETUP_CONFIG_SCRIPT が見つかりません。設定ファイルの作成をスキップします。"
        return 1
    fi

    echo "--- サーバー接続情報の設定を開始します ---"
    python3 "$SETUP_CONFIG_SCRIPT"

    if [ $? -ne 0 ]; then
        echo "❌ 設定ファイルの作成中にエラーが発生しました。"
        return 1
    fi
    return 0
}

# =================================================================
# メイン処理の実行
# =================================================================

# 1. 開発ツールをインストール
install_tools

# 2. direnvのフック設定
setup_direnv_hook

# 3. direnvの設定ファイル（.envrc）の処理
setup_envrc

# 4. その他の設定ファイルテンプレートをコピー
echo "--- その他の設定ファイルテンプレートのコピーを開始します ---"
#copy_config_file "intman.yaml.sample" "intman.yaml"
#copy_config_file "deadman.conf.sample" "deadman.conf"

# 5. Pythonの依存関係をインストール
install_python_deps
if [ $? -ne 0 ]; then exit 1; fi

# 6. 設定ファイル生成スクリプトの実行
run_config_script
if [ $? -ne 0 ]; then exit 1; fi


echo "✅ 全てのセットアップが正常に完了しました！"
echo "---"
echo "次のステップ: 新しいターミナルを開くか、'source ~/.bashrc' を実行してから、プロジェクト作業を開始してください。"

exit 0
