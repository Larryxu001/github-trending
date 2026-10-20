"""Refresh download links and counts without regenerating historical report content."""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from render_html import masthead_info
from render_saved import render
from run_daily import build_web_index


def main():
    pages = list((BASE / 'reports_web').glob('*/*/index.html'))
    for path in pages:
        report = json.loads((BASE / 'data' / (path.parent.name + '.json')).read_text())
        text = path.read_text()
        text = re.sub(r'<i>·</i>\s*<a class="site release-download"[^>]*>.*?</a>', '', text)
        text = re.sub(
            r'(<a class="site source-download" href="https://github.51vipai.com/download/([^"<>]+)\.zip"[^>]*>下载源码 ZIP</a>)',
            lambda m: m[1] + '<i>·</i><a class="site release-download" href="https://github.51vipai.com/release/' + m[2] + '">最新 Release 下载</a>', text)
        text = re.sub(r'<div class="dateline">.*?</div>', lambda m: '<div class="dateline">' + masthead_info(report)[2] + '</div>', text)
        count = sum(len(c['items']) for c in report['categories'])
        if text.count('class="site release-download"') != count:
            raise RuntimeError(f'Missing release links: {path}')
        path.write_text(text)
    config = json.loads((BASE / 'save_config.json').read_text())
    (BASE / 'reports_web/saved.html').write_text(render(config['save_api']))
    build_web_index()
    print(f'Updated {len(pages)} historical reports, saved page and archive.')


if __name__ == '__main__':
    main()
