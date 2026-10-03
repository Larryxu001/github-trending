# github-trending

Daily analysis of GitHub Trending's daily, weekly, and monthly lists, delivered to Feishu and archived in this repository.

## What it does

Every day at 09:00 Beijing time, GitHub Actions automatically:

1. Fetches GitHub Trending's daily, weekly, and monthly lists.
2. Applies **30-day deduplication** using `pushed.json`, avoiding repeat delivery of the same project within a month.
3. Analyzes each new project's developer, stars, website, latest update, purpose, and category.
4. Reuses descriptions already in `desc_cache.json` to avoid duplicate work.
5. Renders a Chinese Markdown daily report and a polished web edition.
6. Sends the report to a Feishu group bot.
7. Archives it in this repository and rebuilds the index.

## Directory structure

```
fetch_trending.py      Fetch lists and deduplicate → items.json
prepare_report.py      Build skeleton and reuse descriptions → report.json / pending.json
desc_auto.py           Generate Chinese descriptions (built-in map and heuristic templates)
apply_desc.py          Merge descriptions → report.json + desc_cache.json
render_html.py         report.json → newspaper-style web edition
render_md.py           report.json → Markdown
push.py                Send Feishu interactive cards
run_daily.py           Daily Actions pipeline entry point
pipeline.sh            Local two-stage pipeline (prepare / finalize)
build_monthly.py       Build monthly report from the month's archives
desc_cache.json        Description cache (repo → category/emoji/description/website)
pushed.json            30-day deduplication history
reports/YYYY/          Daily Markdown archive
reports_web/YYYY/      Web archive and index
data/YYYY-MM-DD.json   Structured data
archive/               Current month's daily archive, used by monthly reports
state/                 State snapshots
```

## Web edition

Hosted free on GitHub Pages: **https://larryxu001.github.io/github-trending/**

Daily and monthly web reports are archived in `reports_web/` and deployed automatically by `pages.yml`.

## Configuration

- **Feishu webhook**: store it in GitHub Secrets as `FEISHU_WEBHOOK`, injected through the runtime environment.
  **Never commit it**; keep feishu_webhook empty in `config.json`.
- **GitHub token**: the workflow injects `${{ github.token }}` as the `GH_TOKEN` environment variable
  to increase GitHub API limits. Public repository data itself does not require an additional token.
- **DeepSeek API key** (optional): store `DEEPSEEK_API_KEY` in GitHub Secrets for AI-generated Chinese summaries and categories.
  **When absent, generation falls back automatically** to built-in rules and templates, at no cost but with lower description quality.
- For local development, put actual configuration in `config.local.json`, which is ignored by .gitignore.

## Manual execution

In the repository's **Actions** tab, select `Daily Trending Report` or `Monthly Trending Report`, then **Run workflow**.

## Notes

- The deduplication window is 30 days; older entries in `pushed.json` are removed automatically.
- Descriptions use AI when `DEEPSEEK_API_KEY` is configured (recommended); otherwise they use a curated built-in map and
  heuristic classification templates based on topics/language. To improve a project's description manually,
  edit `DESC_MAP` in `desc_auto.py` or `desc_cache.json`, then commit the change.
- Delivery channel: **Feishu only**; WeCom has been removed.
- Daily reports run at 09:00 Beijing time, equivalent to cron `0 1 * * *` in UTC.
- Monthly reports run at 09:00 on the month's final day, using cron `0 1 28-31 * *` with an in-program month-end check.
