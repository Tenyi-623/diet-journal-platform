import unittest
from backend.food_import import parse_value

class FoodValuesTest(unittest.TestCase):
    def test_trace_and_missing_are_not_zero(self):
        for raw in ['Tr','(Tr)','-',None,'*']:
            self.assertIsNone(parse_value(raw)['value'])
        self.assertEqual(parse_value('0')['value'],'0')
    def test_estimate_and_footnote_survive(self):
        self.assertTrue(parse_value('(0)')['estimated'])
        self.assertEqual(parse_value('20.3†')['footnote'],'†')
        self.assertEqual(parse_value('20.3†')['value'],'20.3')
    def test_unrecognized_fails_closed(self):
        for raw in ['12 mg','NaN','1,000','-1']:
            with self.assertRaises(ValueError):parse_value(raw)
