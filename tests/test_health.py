import unittest
from unittest.mock import patch
import health_check

class HealthTest(unittest.TestCase):
    def test_unchanged_failure_does_not_repeat_alert(self):
        with patch.object(health_check,'problems',return_value=['same failure']), patch.object(health_check,'load',return_value={'errors':['same failure']}), patch.object(health_check,'write',side_effect=AssertionError('unexpected write')):
            health_check.run()
    def test_changed_failure_persists_before_alert(self):
        events=[]
        with patch.object(health_check,'problems',return_value=['Worker PAT invalid']), patch.object(health_check,'load',return_value={}), patch.object(health_check,'write',side_effect=lambda *a:events.append(('write',a[1]['notification']))), patch('report_jobs.checkpoint',side_effect=lambda *a:events.append(('persist',None))), patch('report_jobs.send_once',side_effect=lambda *a:events.append(('send',None))):
            health_check.run()
        self.assertLess(events.index(('persist',None)),events.index(('send',None)))
        self.assertIn(('write','sent'),events)
