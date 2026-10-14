"""Small warm-model queue observation at 1/2/5 requests; synthetic off-topic messages."""
import asyncio,csv,json,time,uuid
from pathlib import Path
import httpx
async def main():
 accounts=list(csv.DictReader(Path('data/private/local-accounts.csv').open()));groups=[]
 async def single(account,message):
  async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=15) as client:
   r=await client.post('/api/auth/login',json={'login_id':account['login_id'],'password':account['initial_password']});r.raise_for_status();client.headers['X-CSRF-Token']=r.json()['csrf']
   start=time.monotonic();r=await client.post('/api/diet-chat/messages',json={'message':message,'idempotency_key':uuid.uuid4().hex});r.raise_for_status();jid=r.json()['job_id']
   while time.monotonic()-start<180:
    r=await client.get('/api/recommendation-jobs/'+jid);r.raise_for_status();job=r.json()
    if job['status'] not in ['queued','running']:break
    await asyncio.sleep(.2)
   await client.post('/api/auth/logout',json={})
   return {'seconds':round(time.monotonic()-start,3),'status':job['status'],'scope_explained':job.get('result',{}).get('reason_code')=='outside_diet_scope' and bool(job.get('result',{}).get('next_steps'))}
 for n in [1,2,5]:
  rows=await asyncio.gather(*(single(accounts[43+i],['推荐电影','Recommend a movie','映画を紹介して'][i%3]) for i in range(n)))
  times=sorted(x['seconds'] for x in rows);groups.append({'concurrency':n,'observations':rows,'median_seconds':times[len(times)//2],'maximum_seconds':max(times)})
  print(n,rows,flush=True)
 Path('docs/evaluation/queue-performance.json').write_text(json.dumps({'model_state':'warm; not a cold-start benchmark','scope':'small off-topic classification jobs; excludes RAG and long answers; sample too small for a reliable P95','groups':groups},ensure_ascii=False,indent=2))
asyncio.run(main())
