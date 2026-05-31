#!/usr/bin/env python3
"""Generate playlist JSON from .txt files in playlists/ folders.

Usage:
  python generate_playlists.py              # auto-scan playlists/
  python generate_playlists.py -i playlists # explicit input

Scans playlists/ directory:
  playlists/*.txt          -> "Home" topic
  playlists/basketball/    -> "Basketball" topic
  playlists/cooking/       -> "Cooking" topic

Each .txt file becomes a category (filename stem = key).
Each line: name,URL  or  name,timestamps
Output: public/playlists.json
"""

import argparse
import json
import re
from pathlib import Path


def parse_playlist_file(filepath):
    entries = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Check for quoted value: name,"url,time1,time2(label),..."
            m = re.match(r'^([^,]*),\s*"(.+)"$', line)
            if m:
                name = m.group(1).strip()
                inner = m.group(2).strip()
                # First item is URL, rest are times
                parts = [p.strip() for p in inner.split(',')]
                url = parts[0]
                times = []
                for t in parts[1:]:
                    if not t:
                        continue
                    tm = re.match(r'^([\d:]+)\s*(?:\(([^)]*)\))?(.*)$', t)
                    if tm:
                        time_str = tm.group(1)
                        label = (tm.group(2) or '').strip()
                        trailing = (tm.group(3) or '').strip()
                        entry = {'time': time_str}
                        if label:
                            entry['label'] = label
                        if trailing:
                            entry['note'] = trailing
                        times.append(entry)
            else:
                # Simple format: name,url  OR  name,time1,time2,...
                parts = line.split(',', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    rest = parts[1].strip()
                else:
                    rest = parts[0].strip()
                    name = ''
                # Check if rest is timestamps (no URL)
                is_url = bool(re.match(r'^https?://', rest) or re.match(r'^/', rest))
                if not is_url and re.match(r'^\d{1,2}:\d{2}', rest):
                    # Timestamps for a previous entry with the same name
                    time_parts = [p.strip() for p in rest.split(',')]
                    times = []
                    for t in time_parts:
                        if not t:
                            continue
                        tm = re.match(r'^([\d:]+)\s*(?:\(([^)]*)\))?(.*)$', t)
                        if tm:
                            time_str = tm.group(1)
                            label = (tm.group(2) or '').strip()
                            trailing = (tm.group(3) or '').strip()
                            tentry = {'time': time_str}
                            if label:
                                tentry['label'] = label
                            if trailing:
                                tentry['note'] = trailing
                            times.append(tentry)
                    if times and name:
                        for existing in entries:
                            if existing['name'] == name:
                                existing.setdefault('times', []).extend(times)
                                break
                        entries.append({'name': name, 'times': times, 'type': 'text'})
                    continue
                url = rest
                times = []
            if not url:
                continue
            if not name:
                # Derive name from URL
                name = url.rstrip('/').split('/')[-1]
                name = name.split('?')[0]
                if '.' in name:
                    name = name.rsplit('.', 1)[0]
                name = name.replace('_', ' ').replace('-', ' ').strip()
            entry = {'name': name, 'url': url}
            if times:
                entry['times'] = times
            entries.append(entry)
    return entries


def main():
    parser = argparse.ArgumentParser(description='Generate playlist JSON from .txt folders')
    parser.add_argument('-i', '--input', default=None,
                        help='Specific input folder (default: auto-scan playlists/)')
    parser.add_argument('-o', '--output', default=None,
                        help='Output JSON file (default: public/playlists.json)')
    args = parser.parse_args()

    if args.input:
        input_dir = Path(args.input)
    else:
        input_dir = Path('playlists')

    if not input_dir.is_dir():
        print(f'No {input_dir}/ directory found.')
        return 1

    output_path = Path(args.output) if args.output else Path('./public/playlists.json')

    all_playlists = {}
    topics = []

    # Root-level txt files -> "Home" topic
    root_txts = sorted(input_dir.glob('*.txt'))
    if root_txts:
        print('Processing playlists/ (root) -> Home:')
        categories = {}
        for txt_file in root_txts:
            category = txt_file.stem
            entries = parse_playlist_file(txt_file)
            categories[category] = entries
            print(f'    {category}: {len(entries)} video(s)')
        all_playlists['Home'] = categories
        topics.append('Home')

    # Each subfolder -> its own topic
    subdirs = sorted([d for d in input_dir.iterdir()
                      if d.is_dir() and not d.name.startswith('.')])
    for subdir in subdirs:
        label = subdir.name.replace('_', ' ').replace('-', ' ').title()
        print(f'Processing playlists/{subdir.name}/ -> {label}:')
        txt_files = sorted(subdir.glob('*.txt'))
        if not txt_files:
            print(f'  No .txt files found')
            continue
        categories = {}
        for txt_file in txt_files:
            category = txt_file.stem
            entries = parse_playlist_file(txt_file)
            categories[category] = entries
            print(f'    {category}: {len(entries)} video(s)')
        all_playlists[label] = categories
        topics.append(label)

    # Write playlists.json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_playlists, f, indent=2, ensure_ascii=False)
    print(f'\n-> Wrote {len(all_playlists)} topic(s) to {output_path}')
    print(f'Done. Processed {len(all_playlists)} topic(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
