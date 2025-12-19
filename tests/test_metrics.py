import unittest
from hac.analysis_metrics import compute_metrics_from_segments

class DummySeg:
    def __init__(self, start, end, words):
        self.start = start
        self.end = end
        self.words = words

class MetricsTest(unittest.TestCase):
    def test_basic_metrics(self):
        segs = [DummySeg(0.0, 5.0, ['привет','это','тест']), DummySeg(6.5, 11.0, ['еще','один','тест'])]
        fillers = {'это'}
        m = compute_metrics_from_segments(segs, fillers)
        self.assertIn('wpm', m)
        self.assertEqual(m['total_words'], 6)
        self.assertGreater(m['duration_s'], 0)
        self.assertEqual(m['filler_count'], 1)

if __name__ == '__main__':
    unittest.main()
