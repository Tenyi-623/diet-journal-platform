"""Regression cases from the source PDF; require the local repair assets."""
import unittest
from pathlib import Path

import pymupdf
from fontTools.ttLib import TTFont

from backend.dri_text import restore_page
from backend.repair_dri import SOURCE, ROOT, OUTPUT, normalize_japanese


class TextTests(unittest.TestCase):
    def test_normalization_preserves_numbers_and_units(self):
        self.assertEqual(normalize_japanese('食事 摂取 基準 1.8~2.3 mg/dL'), '食事摂取基準 1.8~2.3 mg/dL')


@unittest.skipUnless((OUTPUT/'pages/0273.tsv').exists(),'OCR fixtures not generated')
class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        font=TTFont(ROOT/'.tools/fonts/BIZUDPGothic-Regular.ttf')
        cls.mapping={font.getGlyphID(g):chr(u) for u,g in font.getBestCmap().items()}
        cls.pdf=pymupdf.open(SOURCE)

    @classmethod
    def tearDownClass(cls):
        cls.pdf.close()

    def test_cover_is_restored_from_font_mapping(self):
        text,*_=restore_page(self.pdf[0],1,self.mapping)
        self.assertIn('日本人の食事摂取基準（2025 年版）',text)
        self.assertIn('策定検討会報告書',text)
        self.assertIn('令和６年１０月',text)

    def test_range_error_does_not_enter_retrieval(self):
        text,printed,_,_,retrieval,rejected=restore_page(self.pdf[272],273,self.mapping)
        self.assertIn('マグネシウム（Mg）',text)
        self.assertEqual(printed,'261')
        self.assertNotIn('3060%',retrieval)
        self.assertNotIn('30350%',retrieval)
        self.assertTrue(any('50' in r['native_numbers_missing_or_changed'] for r in rejected))

    def test_corrupted_unit_does_not_enter_retrieval(self):
        *_,retrieval,rejected=restore_page(self.pdf[12],13,self.mapping)
        self.assertNotIn('(ks)',retrieval)
        self.assertTrue(any('kg' in r['native_units_missing_or_changed'] for r in rejected))
