import getpass
import os

# 出力ファイルは、setup_config.pyと同じディレクトリ（bin/）に作成される
CONFIG_FILE = "cml_env"

def create_cml_config():
    """ユーザー入力を受け付け、CML接続設定ファイル（cml_env）を生成する"""
    print("--- CML/VIRL 接続情報の設定 ---")

    # 対話的に情報を取得
    # サンプルの値をデフォルトとして提示
    server_ip = input("CML/VIRL のIPアドレスを入力してください (例: 192.168.122.212): ") or "192.168.122.212"
    username = input("ユーザー名を入力してください (例: admin): ") or "admin"

    # パスワードは入力内容を隠すgetpassを使用
    try:
        password = getpass.getpass("パスワードを入力してください (例: Cisco123): ") or "Cisco123"
    except EOFError:
        print("\n入力が途中で中断されました。")
        return

    # 設定内容をシェル環境変数形式でフォーマット
    config_content = f'''
# このファイルは bin/setup_config.py によって生成されました。
# 環境変数として使用されます。

VIRL_HOST="{server_ip}"
VIRL2_USER="{username}"
VIRL2_PASS="{password}"
'''

    # 設定ファイルを書き込み
    try:
        # スクリプトと同じディレクトリ（bin/）に出力
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, CONFIG_FILE)

        with open(output_path, 'w') as f:
            f.write(config_content.strip())

        # ファイルのパーミッションを設定 (実行可能にする必要があれば chmod +x)
        # 通常、環境変数を source するだけなら実行権限は不要ですが、念のため644に設定
        os.chmod(output_path, 0o644)

        print(f"\n✅ 設定ファイル '{output_path}' を正常に作成しました。")
    except IOError as e:
        print(f"\n❌ 設定ファイルの書き込みに失敗しました: {e}")

if __name__ == "__main__":
    create_cml_config()