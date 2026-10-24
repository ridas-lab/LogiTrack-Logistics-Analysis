"""Download the four official Olist CSV tables used in the Week 2 exercise."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import hashlib
import json
import argparse
from datetime import datetime, timezone

COMMIT = 'd9e49802f3e92d09ee94ab9ccc5e457f207a8959'
BASE = f'https://raw.githubusercontent.com/olist/work-at-olist-data/{COMMIT}/'
FILES = [f'datasets/olist_{name}_dataset.csv' for name in
         ['orders', 'order_items', 'customers', 'products']]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent/'data')
    args = parser.parse_args()
    args.data_dir.mkdir(parents=True, exist_ok=True)
    def download(relative):
        target = args.data_dir/Path(relative).name
        url = BASE+relative
        with urlopen(Request(url,headers={'User-Agent':'logistics-coursework'}),timeout=120) as response:
            body=response.read()
        target.write_bytes(body)
        return {'file':target.name,'url':url,'bytes':len(body),
                'sha256':hashlib.sha256(body).hexdigest()}
    with ThreadPoolExecutor(max_workers=4) as pool:
        manifest=list(pool.map(download,FILES+['README.md','LICENSE']))
    info={'repository':'https://github.com/olist/work-at-olist-data',
          'commit':COMMIT,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'files':manifest}
    (args.data_dir/'source_manifest.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print(json.dumps(info,indent=2))

if __name__ == '__main__':
    main()
