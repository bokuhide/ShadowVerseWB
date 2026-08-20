param(
    [string]$OutputDirectory = "data"
)

$ErrorActionPreference = "Stop"
$SourcePage = "https://shadowverse-wb.com/ja/deck/cardslist/"
$ApiUrl = "https://shadowverse-wb.com/web/CardList/cardList"
$PageSize = 30
$Headers = @{ Accept = "application/json"; Lang = "ja" }

$ClassNames = @{
    "0" = "ニュートラル"; "1" = "エルフ"; "2" = "ロイヤル"; "3" = "ウィッチ"
    "4" = "ドラゴン"; "5" = "ナイトメア"; "6" = "ビショップ"; "7" = "ネメシス"
}
# Official display code maps raw API types 2 and 3 to amulet, and 4 to spell.
$TypeNames = @{ "1" = "フォロワー"; "2" = "アミュレット"; "3" = "アミュレット"; "4" = "スペル" }
$RarityNames = @{
    "1" = "ブロンズレア"; "2" = "シルバーレア"; "3" = "ゴールドレア"; "4" = "レジェンド"
}

function Get-OfficialPage([int]$Offset) {
    $uri = "$ApiUrl`?offset=$Offset"
    for ($attempt = 0; $attempt -lt 4; $attempt++) {
        try {
            return Invoke-RestMethod -UseBasicParsing -Headers $Headers -Uri $uri -TimeoutSec 90
        } catch {
            if ($attempt -eq 3) { throw }
            Start-Sleep -Seconds ([math]::Pow(2, $attempt))
        }
    }
}

function ConvertTo-PlainText($Value) {
    if ([string]::IsNullOrEmpty($Value)) { return "" }
    $text = [string]$Value
    $text = [regex]::Replace($text, '<ruby[^>]*>(.*?)<rt>.*?</rt></ruby>', '$1', 'Singleline')
    $text = [regex]::Replace($text, '<hr\s*/?>', "`n", 'IgnoreCase')
    $text = [regex]::Replace($text, '</?(?:color|ev|sev|ridx)(?:=[^>]*)?>', '')
    $text = [regex]::Replace($text, '<[^>]+>', '')
    $text = [System.Net.WebUtility]::HtmlDecode($text)
    $text = $text -replace "`r`n?", "`n"
    $text = [regex]::Replace($text, "`n{3,}", "`n`n")
    return $text.Trim()
}

$first = Get-OfficialPage 0
$expectedCount = [int]$first.data.count
$cardSets = $first.data.card_set_names
$cards = [System.Collections.Generic.List[object]]::new()
$seen = [System.Collections.Generic.HashSet[int]]::new()

for ($offset = 0; $offset -lt $expectedCount; $offset += $PageSize) {
    $data = if ($offset -eq 0) { $first.data } else { (Get-OfficialPage $offset).data }
    foreach ($listedId in $data.sort_card_id_list) {
        $cardId = [int]$listedId
        if (-not $seen.Add($cardId)) { throw "Duplicate card_id=$cardId" }
        $detail = $data.card_details.PSObject.Properties[[string]$cardId].Value
        if ($null -eq $detail) { throw "Missing detail for listed card_id=$cardId" }
        $common = $detail.common
        $typeId = [int]$common.type
        if (-not $TypeNames.ContainsKey([string]$typeId)) { throw "Unexpected type=$typeId for card_id=$cardId" }
        $isFollower = $typeId -eq 1
        $evoEffect = if ($isFollower -and $null -ne $detail.evo) {
            ConvertTo-PlainText $detail.evo.skill_text
        } elseif ($isFollower) { "" } else { $null }
        $cards.Add([ordered]@{
            card_id = $cardId
            "カード名" = ConvertTo-PlainText $common.name
            "クラス" = $ClassNames[[string]$common.class]
            "コスト" = [int]$common.cost
            "種類" = $TypeNames[[string]$typeId]
            "攻撃" = if ($isFollower) { [int]$common.atk } else { $null }
            "体力" = if ($isFollower) { [int]$common.life } else { $null }
            "効果" = ConvertTo-PlainText $common.skill_text
            "進化後効果" = $evoEffect
            card_set = $cardSets.PSObject.Properties[[string]$common.card_set_id].Value
            card_set_id = [int]$common.card_set_id
            rarity = $RarityNames[[string]$common.rarity]
            rarity_id = [int]$common.rarity
        })
    }
}

if ($cards.Count -ne $expectedCount) {
    throw "Expected $expectedCount cards, collected $($cards.Count)"
}

$metadata = [ordered]@{
    retrieved_at = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    language = "ja"
    official_source_url = $SourcePage
    official_api_url = $ApiUrl
    card_count = $cards.Count
    unique_card_id_count = $seen.Count
    collection_method = "The official card-list JavaScript calls GET /web/CardList/cardList. This collector follows that endpoint in 30-card pages using offset, preserves sort_card_id_list order, and selects only those listed IDs from card_details."
    scope = "Cards returned by the Japanese official card library's default search. Related/generated token details bundled by the API are not added unless their IDs occur in sort_card_id_list."
    schema = [ordered]@{
        card_id = "integer; official unique card ID"
        "カード名" = "string"
        "クラス" = "string"
        "コスト" = "integer"
        "種類" = "フォロワー | スペル | アミュレット"
        "攻撃" = "integer for followers; null otherwise"
        "体力" = "integer for followers; null otherwise"
        "効果" = "string; official markup converted to plain text"
        "進化後効果" = "string for followers, possibly empty; null otherwise"
        card_set = "string; Japanese official set name"
        card_set_id = "integer"
        rarity = "ブロンズレア | シルバーレア | ゴールドレア | レジェンド"
        rarity_id = "integer"
    }
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$cardsJson = $cards | ConvertTo-Json -Depth 10
$metadataJson = $metadata | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText((Join-Path $OutputDirectory "cards.json"), $cardsJson + "`n", $utf8NoBom)
[System.IO.File]::WriteAllText((Join-Path $OutputDirectory "metadata.json"), $metadataJson + "`n", $utf8NoBom)
Write-Output "Wrote $($cards.Count) unique cards to $(Join-Path $OutputDirectory 'cards.json')"
