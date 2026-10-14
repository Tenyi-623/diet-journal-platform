"""Read back every imported value and compare against validated source staging."""
import json
from decimal import Decimal
from backend.food_import import DATA
from backend.knowledge import connect

staging=json.loads((DATA/'validated.json').read_text())
eligible=[f for f in staging['foods'] if f['validation_status']=='ready']
expected={(f['code'],code):(None if v['value'] is None else Decimal(v['value']),v['raw'],v['status'],v['estimated'],v['footnote'])
    for f in eligible for code,v in f['nutrients'].items()}
with connect() as conn:
    dataset=conn.execute('SELECT id FROM food_datasets WHERE sha256=%s',(staging['source']['sha256'],)).fetchone()['id']
    rows=conn.execute('SELECT * FROM food_values WHERE dataset_id=%s',(dataset,)).fetchall()
    actual={(r['food_code'],r['nutrient_code']):(r['value'],r['raw'],r['status'],r['estimated'],r['footnote']) for r in rows}
    assert actual==expected
    stored=conn.execute('SELECT code,source FROM foods WHERE dataset_id=%s',(dataset,)).fetchall()
    assert len(stored)==len(eligible)
    by_code={f['code']:f for f in eligible}
    for row in stored:
        assert row['source']=={k:v for k,v in by_code[row['code']].items() if k!='nutrients'}
    nutrients=conn.execute('SELECT metadata FROM food_nutrients WHERE dataset_id=%s ORDER BY code',(dataset,)).fetchall()
    assert [r['metadata'] for r in nutrients]==sorted(staging['nutrients'],key=lambda n:n['code'])
    assert not any(r['code']=='01210' for r in stored)
    kb=conn.execute('SELECT count(*) n FROM kb_chunks').fetchone()['n']
print(json.dumps({'dataset_id':dataset,'foods_verified':len(stored),'values_verified':len(actual),
    'pdf_and_excel_provenance_verified':True,'quarantined_01210_excluded':True,'existing_kb_chunks':kb}))
