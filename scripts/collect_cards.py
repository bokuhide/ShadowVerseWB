#!/usr/bin/env python3
"""Collect the public Japanese Deck Portal using only Python's standard library."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen

API = 'https://shadowverse-wb.com/web/CardList/cardList'
SOURCE = 'https://shadowverse-wb.com/ja/deck/cardslist/'
IMAGE = 'https://shadowverse-wb.com/uploads/card_image/jpn/card'
CLASSES = ['ニュートラル', 'エルフ', 'ロイヤル', 'ウィッチ', 'ドラゴン', 'ナイトメア', 'ビショップ', 'ネメシス']
TYPES = {1: 'フォロワー', 2: 'アミュレット', 3: 'アミュレット', 4: 'スペル'}
RARITIES = {1: 'ブロンズレア', 2: 'シルバーレア', 3: 'ゴールドレア', 4: 'レジェンド'}


def plain(value):
    value = re.sub(r'<ruby[^>]*>(.*?)<rt>.*?</rt></ruby>', r'\1', value or '', flags=re.S)
    value = re.sub(r'<hr\s*/?>', '\n', value, flags=re.I)
    value = re.sub(r'<[^>]+>', '', value)
    return re.sub(r'\n{3,}', '\n\n', html.unescape(value).replace('\r\n', '\n').replace('\r', '\n')).strip()


def image(value):
    return f'{IMAGE}/{value}.png' if value else None


def collect(cache, rotation=False):
    prefix = 'rotation' if rotation else 'page'
    pages, ids, details, sources = [], [], {}, []
    offset, expected = 0, None
    while expected is None or offset < expected:
        url = f'{API}?offset={offset}' + ('&battle_format=1' if rotation else '')
        target = cache / f'{prefix}_{offset:04}.json' if cache else None
        if target and target.exists():
            raw = target.read_bytes()
        else:
            for attempt in range(3):
                try:
                    with urlopen(Request(url, headers={'Accept': 'application/json', 'Lang': 'ja'}), timeout=45) as response:
                        raw = response.read()
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
            if target:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        data = json.loads(raw)['data']
        assert data['result_error_code'] is None, url
        if expected is None:
            expected = data['count']
        assert data['count'] == expected, 'Source count changed during collection'
        listed = [int(x) for x in data['sort_card_id_list']]
        assert len(listed) == min(30, expected - offset), url
        ids.extend(listed)
        for card_id in listed:
            details[card_id] = data['card_details'][str(card_id)]
        pages.append(data)
        acquired = datetime.fromtimestamp(target.stat().st_mtime, timezone.utc) if target else datetime.now(timezone.utc)
        sources.append({'url': url, 'listed_count': len(listed), 'sha256': hashlib.sha256(raw).hexdigest(),
                        'retrieved_at': acquired.isoformat(timespec='milliseconds').replace('+00:00', 'Z')})
        offset += 30
    assert len(ids) == len(set(ids)) == expected, 'Duplicate/missing listed IDs'
    return ids, details, pages[0]['card_set_names'], sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, default=Path('data'))
    parser.add_argument('--cache-directory', type=Path, help='Optional raw-response cache for reproducible processing; use a fresh directory for a new acquisition')
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    ids, details, sets, sources = collect(args.cache_directory)
    rotation_ids, _, _, rotation_sources = collect(args.cache_directory, rotation=True)
    cards = []
    for card_id in ids:
        detail = details[card_id]
        c = detail['common']
        evo = detail.get('evo') or {}
        follower = c['type'] == 1
        assert c['card_id'] == card_id and not c['is_token']
        assert isinstance(c['is_include_rotation'], bool)
        effect = plain(c['skill_text'])
        styles = []
        for i, s in enumerate(detail.get('style_card_list') or [], 1):
            override = plain(s.get('skill_text'))
            styles.append({
                'style_index': i, 'style_name': plain(s.get('name')), 'style_name_ruby': plain(s.get('name_ruby')),
                'image_hash': s.get('hash') or '', 'image_url': image(s.get('hash')),
                'evolved_image_hash': s.get('evo_hash') or None, 'evolved_image_url': image(s.get('evo_hash')),
                'effect_override': override or None, 'effective_effect': override or effect,
                'uses_base_effect': not bool(override), 'flavour_text': plain(s.get('flavour_text')),
                'evolved_flavour_text': plain(s.get('evo_flavour_text')), 'cv': s.get('cv') or '',
                'illustrator': s.get('illustrator') or '',
            })
        cards.append({
            'card_id': card_id, 'カード名': plain(c['name']), 'クラス': CLASSES[c['class']],
            'コスト': c['cost'], '種類': TYPES[c['type']], '攻撃': c['atk'] if follower else None,
            '体力': c['life'] if follower else None, '効果': effect,
            '進化後効果': plain(evo.get('skill_text')) if follower else None,
            'card_set': sets[str(c['card_set_id'])], 'card_set_id': c['card_set_id'],
            'rarity': RARITIES[c['rarity']], 'rarity_id': c['rarity'],
            'image_hash': c.get('card_image_hash') or '', 'image_url': image(c.get('card_image_hash')),
            'evolved_image_hash': evo.get('card_image_hash') or None, 'evolved_image_url': image(evo.get('card_image_hash')),
            'card_styles': styles, 'is_include_rotation': c['is_include_rotation'],
        })
    flagged = {c['card_id'] for c in cards if c['is_include_rotation']}
    assert flagged == set(rotation_ids), 'Per-card flags and official rotation search disagree'
    assert set(rotation_ids) <= set(ids)
    output = args.output_directory
    output.mkdir(parents=True, exist_ok=True)
    metadata_path = output / 'metadata.json'
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {'schema': {}}
    ended = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    set_counts = []
    for set_id, name in sets.items():
        members = [c for c in cards if c['card_set_id'] == int(set_id)]
        set_counts.append({'card_set_id': int(set_id), 'card_set': name, 'card_count': len(members),
                           'rotation_card_count': sum(c['is_include_rotation'] for c in members)})
    acquired = max(p['retrieved_at'] for p in sources + rotation_sources)
    metadata.update({
        'retrieved_at': acquired, 'processed_at': ended, 'language': 'ja', 'official_source_url': SOURCE, 'official_api_url': API,
        'card_count': len(cards), 'unique_card_id_count': len(ids),
        'cards_with_styles': sum(bool(c['card_styles']) for c in cards),
        'card_style_count': sum(len(c['card_styles']) for c in cards),
        'rotation_card_count': len(rotation_ids), 'non_rotation_card_count': len(cards) - len(rotation_ids),
        'card_sets': set_counts,
        'collection_method': 'Python standard library; GET /web/CardList/cardList in 30-card offset pages. Only sort_card_id_list IDs are normalized; related tokens and styles are not counted as separate cards. Rotation flags are cross-checked against all battle_format=1 pages.',
        'scope': 'All cards in the Japanese official default search, including historical sets. is_include_rotation describes the portal snapshot, not a separately verified release or maintenance effective date.',
        'source_pages': sources, 'rotation_source_pages': rotation_sources,
        'processing_started_at': started,
    })
    metadata['schema']['is_include_rotation'] = 'boolean; common.is_include_rotation from official API, cross-checked against battle_format=1; snapshot availability flag, not a release-date guarantee'
    rotation = {'retrieved_at': acquired, 'official_source_url': SOURCE + '?battle_format=1',
                'official_api_url': API + '?battle_format=1', 'card_count': len(rotation_ids),
                'card_ids': rotation_ids, 'scope': metadata['scope']}
    for name, obj in [('cards.json', cards), ('metadata.json', metadata), ('rotation.json', rotation)]:
        (output / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'cards': len(cards), 'rotation_cards': len(rotation_ids), 'card_sets': set_counts}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
