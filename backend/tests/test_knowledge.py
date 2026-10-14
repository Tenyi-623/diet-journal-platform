import unittest

import httpx

from backend.embeddings import embed_texts
from backend.ingest import chunk_text, page_reason
from backend.knowledge_api import SearchRequest
from pydantic import ValidationError


class ChunkTests(unittest.TestCase):
    def test_chunks_cover_text_without_gaps(self):
        text = ''.join(chr(0x4e00 + i) for i in range(2400))
        chunks = list(chunk_text(text))
        self.assertTrue(all(len(c) <= 1000 for c in chunks))
        self.assertEqual(chunks[0], text[:1000])
        self.assertEqual(chunks[1][:150], chunks[0][-150:])
        self.assertTrue(text.endswith(chunks[-1]))
        self.assertEqual(''.join([chunks[0]] + [c[150:] for c in chunks[1:]]), text)

    def test_quarantined_source_never_eligible(self):
        self.assertEqual(page_reason('正常な文章。'*100, {'quarantine':True,'warning':'old'}), 'old')

    def test_table_is_not_retrievable(self):
        source = {'quarantine':False,'source_kind':'food_composition_reference'}
        self.assertTrue(page_reason('食品番号 索引番号\n' + '12345\n'*100,source))

    def test_search_validation(self):
        for body in ({'query':' '},{'query':'test','top_k':21},{'query':'test','document_id':-1}):
            with self.assertRaises(ValidationError):
                SearchRequest(**body)


class EmbeddingTests(unittest.IsolatedAsyncioTestCase):
    async def test_wrong_dimensions_rejected(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda r: httpx.Response(200,json={'embeddings':[[1,2]]})
        )) as client:
            with self.assertRaisesRegex(ValueError,'dimension'):
                await embed_texts(client,base_url='http://test',model='test',texts=['a'],expected_dim=2560)

    async def test_batch_count_rejected(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda r: httpx.Response(200,json={'embeddings':[]})
        )) as client:
            with self.assertRaisesRegex(ValueError,'count'):
                await embed_texts(client,base_url='http://test',model='test',texts=['a'],expected_dim=2560)


if __name__ == '__main__':
    unittest.main()
