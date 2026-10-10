# ShadowVerseWB card data

『Shadowverse: Worlds Beyond』日本語公式カード一覧の構造化データです。

## 成果物

- `data/cards.json`: 公式カード一覧のカード。`card_id` で一意です。
- `data/metadata.json`: 取得日時、公式URL、件数、取得方法、スキーマ。
- `scripts/collect_cards.ps1`: 公式APIから再取得するPowerShellスクリプト。
- `scripts/validate_cards.mjs`: Node.jsで件数・重複・必須項目・画像URLの応答を検証。
- `data/validation.json`: 最新の検証結果（差分は検証時のローカルHEADとの比較）。

必須項目は `カード名`、`クラス`、`コスト`、`種類`、`攻撃`、`体力`、`効果` です。
加えて `card_id`、`card_set`、`rarity` と、それぞれの公式数値ID、進化後効果を保存します。
公式APIに別イラストのカードスタイルがある場合は、元カードの `card_styles` 配列に
スタイル名、画像URL、CV、イラストレーター、フレーバーテキスト、効果差分を保存します。
スタイル名は公式APIの値をそのまま使用するため、API側で名称が未設定のスタイルは空文字です。
カードスタイルは独立カードとして件数に加えず、元カードとの対応を維持します。
スペルとアミュレットの攻撃・体力は `null` です。
通常カードにも `image_hash` / `image_url` と、存在する場合は
`evolved_image_hash` / `evolved_image_url` を保存し、録画の絵柄照合に利用できます。
画像ファイル本体は保存しません。通常一覧外の生成トークンは、このデータの対象外です。

## 再取得

追加ライブラリは不要です。PowerShell 7以降で、リポジトリのルートから実行してください。

```console
pwsh -File scripts/collect_cards.ps1
```

Windows標準TLSで取得できない環境では、証明書検証を維持したままNode.jsの通信を選べます。

```console
pwsh -File scripts/collect_cards.ps1 -NodeExecutable "C:\path\to\node.exe"
node scripts/validate_cards.mjs
```

スクリプトは公式ページが使用している
`https://shadowverse-wb.com/web/CardList/cardList` を30件ずつ取得します。
各ページの `sort_card_id_list` に掲載されたIDだけを採用するため、応答内に関連カードとして
同梱される生成トークンを誤って通常カードとして混ぜません。取得後、公式の件数と一意な
`card_id` 件数が一致しなければエラー終了します。

公式ソース: https://shadowverse-wb.com/ja/deck/cardslist/

## クラウド用の参照資料

`data/official-card-pool` ブランチに、作業ルール・3デッキの現行レシピ・公開プロ試合の目録と9事例を保存しています。入口は [クラウド作業ガイド](docs/cloud/README.md) と [公開用引き継ぎ](knowledge/handoff.md) です。`node scripts/validate_learning.mjs` でカード照合・40枚・事例整合を検証できます。

これは参照資料の蓄積であり、モデルの重みの追加訓練ではありません。個人録画・戦績・非公開シートの情報は含めません。クラウド実行の可否は、別途実測して判断してください。
