import base64
import json
import unittest
import urllib.error
from unittest.mock import patch
import import_project as importer


class ImportTests(unittest.TestCase):
    def test_repository_links_only(self):
        self.assertEqual(importer.parse_repo('https://github.com/a/b.git?tab=readme'), 'a/b')
        for url in ['https://evil.test/a/b', 'http://github.com/a/b', 'https://github.com/a/b/issues', 'https://github.com@evil.test/a/b', 'https://github.com/a']:
            with self.assertRaises(ValueError):
                importer.parse_repo(url)

    def test_duplicate_preserves_user_data_and_never_calls_ai(self):
        with patch.object(importer, 'read_saved', return_value=({'items':[{'repo':'A/B','note':'keep'}]},'sha')), patch.object(importer,'analyse') as ai:
            self.assertIn('已在精选库', importer.import_one('https://github.com/a/b'))
            ai.assert_not_called()

    def test_failed_analysis_does_not_write(self):
        with patch.object(importer,'read_saved',return_value=({'items':[]},'sha')), patch.object(importer,'analyse',side_effect=ValueError('bad AI')), patch.object(importer,'github') as github:
            with self.assertRaises(ValueError):
                importer.import_one('https://github.com/a/b')
            github.assert_not_called()

    def test_conflict_preserves_concurrent_save(self):
        snapshots=[({'items':[]},'old'),({'items':[]},'old'),({'items':[{'repo':'other/project','note':'keep'}]},'new')]
        conflict=urllib.error.HTTPError('https://api.github.com',409,'conflict',{},None)
        with patch.object(importer,'read_saved',side_effect=snapshots), patch.object(importer,'analyse',return_value={'repo':'a/b','desc':'analysis'}), patch.object(importer,'github',side_effect=[conflict,{}]) as github, patch.object(importer.time,'sleep'):
            self.assertIn('已加入精选', importer.import_one('https://github.com/a/b'))
            body=github.call_args.args[1]
            self.assertEqual(body['sha'],'new')
            items=json.loads(base64.b64decode(body['content']))['items']
            self.assertEqual(items[0]['note'],'keep')
            self.assertEqual(items[1]['repo'],'a/b')

    def test_manual_project_enters_weekly_and_monthly(self):
        import datetime
        from report_jobs import weekly_report, monthly_report
        item={'repo':'a/b','saved_at':'2026-10-08','source':'pages','desc':'中文 AI 分析','category':'其他'}
        weekly=weekly_report({'items':[item]}, datetime.date(2026,10,12))
        self.assertEqual(weekly['new_count'],1)
        monthly=monthly_report([weekly],'2026-10')
        self.assertEqual(monthly['new_count'],1)
        self.assertEqual(monthly['categories'][0]['items'][0]['desc'],'中文 AI 分析')

    def test_feishu_notification_uses_content_text(self):
        import io
        response=io.BytesIO(b'{"code":0}')
        with patch.dict(importer.os.environ,{'FEISHU_WEBHOOK':'https://example.invalid'}), patch.object(importer.urllib.request,'urlopen',return_value=response) as send:
            importer.notify('已加入精选')
            body=json.loads(send.call_args.args[0].data)
            self.assertEqual(body,{'msg_type':'text','content':{'text':'已加入精选'}})
