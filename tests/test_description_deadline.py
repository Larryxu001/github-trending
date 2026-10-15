import signal
import time
import unittest
from unittest.mock import patch
import desc_auto


class DescriptionDeadlineTests(unittest.TestCase):
    def test_slow_response_is_interrupted_and_preserves_project_with_fallback(self):
        real_timer = signal.setitimer
        previous_handler = signal.getsignal(signal.SIGALRM)
        def timer(which, seconds):
            return real_timer(which, min(seconds, 0.02))
        project = {'repo': 'test/slow', 'readme_hint': 'A useful public tool', 'homepage': 'https://example.com'}
        with patch.object(desc_auto, '_llm_one', side_effect=lambda p: time.sleep(2)), \
             patch.object(signal, 'setitimer', side_effect=timer):
            started = time.monotonic()
            result = desc_auto.run_llm([project], {})
        self.assertLess(time.monotonic() - started, 1)
        self.assertIn('A useful public tool', result['test/slow']['desc'])
        self.assertEqual(result['test/slow']['site'], 'https://example.com')
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous_handler)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL)[0], 0)

    def test_exhausted_batch_does_not_call_ai(self):
        with patch.object(desc_auto.time, 'monotonic', side_effect=[0, 121]), \
             patch.object(desc_auto, '_llm_one') as call:
            result = desc_auto.run_llm([{'repo': 'test/late'}], {})
        call.assert_not_called()
        self.assertTrue(result['test/late']['desc'])
