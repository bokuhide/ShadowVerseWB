# ShadowVerseWB card data

『Shadowverse: Worlds Beyond』日本語公式カード一覧の構造化データです。

## 成果物

- `data/cards.json`: 公式カード一覧のカード。`card_id` で一意です。
- `data/metadata.json`: 取得日時、公式URL、件数、取得方法、スキーマ。
- `scripts/collect_cards.ps1`: 公式APIから再取得するPowerShellスクリプト。

必須項目は `カード名`、`クラス`、`コスト`、`種類`、`攻撃`、`体力`、`効果` です。
加えて `card_id`、`card_set`、`rarity` と、それぞれの公式数値ID、進化後効果を保存します。
スペルとアミュレットの攻撃・体力は `null` です。

## 再取得

追加ライブラリは不要です。PowerShell 7以降で、リポジトリのルートから実行してください。

```console
pwsh -File scripts/collect_cards.ps1
```

スクリプトは公式ページが使用している
`https://shadowverse-wb.com/web/CardList/cardList` を30件ずつ取得します。
各ページの `sort_card_id_list` に掲載されたIDだけを採用するため、応答内に関連カードとして
同梱される生成トークンを誤って通常カードとして混ぜません。取得後、公式の件数と一意な
`card_id` 件数が一致しなければエラー終了します。

公式ソース: https://shadowverse-wb.com/ja/deck/cardslist/
