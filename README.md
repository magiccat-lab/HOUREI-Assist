# HOUREI-Assist

法令検索MCP Server — e-Gov法令API + FTS5全文検索で条文起草を支援

## 機能

- **search_law**: 法令名キーワード検索
- **get_article**: 条文取得(条/項指定)
- **get_revision**: 改正履歴取得
- **keyword_search**: e-Gov全文検索(AND/OR/NOT/ワイルドカード)
- **search_usage**: FTS5 trigram全文横断検索(ローカルインデックス)
- **search_debate**: 国会議事録検索(立法経緯の確認)
- **similar_articles**: ベクトル類似条文検索(要[vector] extras)

## セットアップ

```bash
pip install -e .

# e-Gov APIの動作確認
hourei-mcp smoke-test

# 全文検索インデックスの構築(オプション)
curl -o laws.zip 'https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true'
unzip laws.zip -d ~/.local/share/hourei-mcp/xml/
hourei-mcp build-index
hourei-mcp check-index
```

## Claude Code / Claude Desktop から使う

```bash
claude mcp add --transport http hourei http://127.0.0.1:8793/mcp
```

## サーバー起動

```bash
hourei-mcp serve
```

systemd常駐:
```bash
cp deploy/systemd/hourei-mcp.service ~/.config/systemd/user/
systemctl --user enable --now hourei-mcp
```

## 開発

```bash
pip install -e ".[dev]"
pytest
```

## ロードマップ

- [x] Phase 1: e-Gov API + FTS5全文検索
- [x] Phase 2: HTTP MCP常駐 + systemd
- [x] Phase 3: 国会議事録API (search_debate)
- [ ] Phase 3b: 通達・通知検索 (search_circular)
- [x] Phase 4: Ruri v3ベクトル検索(コード実装済、要[vector] extras)
