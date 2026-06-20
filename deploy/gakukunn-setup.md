# HOUREI-Assist セットアップ手順 (gakukunnlab/my-claude 向け)

## 前提

- Python 3.11+
- systemd --user 対応
- Claude Code が screen session で稼働中

## 1. インストール

```bash
git clone https://github.com/magiccat-lab/HOUREI-Assist.git ~/HOUREI-Assist
cd ~/HOUREI-Assist
pip install -e .

# ベクトル検索を使う場合 (GPU不要、CPU推論)
# pip install -e ".[vector]"
```

## 2. e-Gov API 疎通確認

```bash
hourei-mcp smoke-test
```

## 3. FTS5 全文検索インデックス構築

```bash
curl -o laws.zip 'https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true'
unzip laws.zip -d ~/.local/share/hourei-mcp/xml/
hourei-mcp build-index
hourei-mcp check-index
```

## 4. Notion ルール連携 (任意)

```bash
mkdir -p ~/.config/hourei-mcp
cp deploy/env.example ~/.config/hourei-mcp/env
# NOTION_API_KEY と HOUREI_RULES_PAGE_ID を設定
```

NOTION_API_KEY: Notion internal integration を作成して取得
HOUREI_RULES_PAGE_ID: ルールを書いたページの ID

## 5. systemd 常駐

```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/hourei-mcp.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hourei-mcp
```

## 6. Claude Code に MCP 登録

```bash
claude mcp add --transport http hourei http://127.0.0.1:8793/mcp
```

## 7. 既存 MCP の整理

HOUREI-Assist は以下を統合済み:
- 法令検索 (search_law, get_article, keyword_search)
- 全文検索 (search_usage — FTS5 trigram)
- 国会議事録 (search_debate)
- ベクトル類似検索 (similar_articles — [vector] extras)
- ルール管理 (get_rules — Notion SSoT)

個別の hourei / kokkai MCP は無効化して OK。
tax-law / labor-law / gyosei は HOUREI-Assist 未統合のため残す。

## 8. opus-max screen 並走 (オプション)

nightly_restart.sh に追加:

```bash
# opus screen (法令起案用)
screen -dmS secretary-opus bash -c 'claude --model opus --dangerously-skip-permissions ...'
```

AGENT/IDENTITY_OPUS.md を新設してキャラ設定を分ける。
