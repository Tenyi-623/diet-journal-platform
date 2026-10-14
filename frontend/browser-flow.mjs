import {chromium} from '@playwright/test';import {readFileSync,writeFileSync} from 'node:fs';
const browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
const [id,password]=readFileSync('../data/private/local-accounts.csv','utf8').trim().split('\n').find(x=>x.startsWith('diet050,')).trim().split(',');
await page.goto('http://127.0.0.1:8000');await page.getByLabel('登录 ID').fill(id);await page.getByLabel('密码').fill(password);await page.getByRole('button',{name:'登录',exact:true}).click();await page.waitForURL('**/home');
await page.goto('http://127.0.0.1:8000/profile');await page.getByLabel('称呼').fill('演示用户');await page.getByLabel('年龄').fill('40');
await page.getByLabel('个人税前年收入（日元）').click();await page.getByRole('option',{name:'0～不满200万日元',exact:true}).click();
await page.getByLabel('过敏情况').click();await page.getByRole('option',{name:'无已知过敏',exact:true}).click();
await page.getByLabel('我已核对上述健康情况（未选表示无上述情况）').check();await page.getByLabel('我理解并确认使用上述演示目标与模拟价格').check();
await page.getByRole('button',{name:'保存信息',exact:true}).click();await page.getByRole('alert').filter({hasText:'已保存'}).waitFor();
await page.goto('http://127.0.0.1:8000/home');await page.locator('.stat-grid').waitFor();await page.screenshot({path:'../docs/evaluation/screenshots/personalized.png',fullPage:true});
await page.goto('http://127.0.0.1:8000/chat');await page.locator('textarea').fill('预算900日元安排一天三餐');await page.getByRole('button',{name:'发送',exact:true}).click();await page.locator('.plan-result').waitFor({timeout:180000});
await page.screenshot({path:'../docs/evaluation/screenshots/plan.png',fullPage:true});await page.reload();await page.locator('.session').first().click();await page.locator('.plan-result').waitFor();
await page.goto('http://127.0.0.1:8000/history');await page.locator('.history-item').first().waitFor();const before=await page.locator('.history-item').count();await page.getByRole('button',{name:'换一道',exact:true}).first().click();await page.waitForFunction(n=>document.querySelectorAll('.history-item').length>n,before,{timeout:180000});
for(const lang of ['en','ja']){await page.getByLabel('Language').selectOption(lang);await page.goto('http://127.0.0.1:8000/home');await page.locator('.recipe-card').first().waitFor();await page.screenshot({path:`../docs/evaluation/screenshots/home-${lang}.png`,fullPage:true});}
writeFileSync('../docs/evaluation/browser-flow.json',JSON.stringify({profileSave:true,personalized:true,chatPlan:true,reloadHistory:true,substitution:true,languages:['zh','en','ja'],errors},null,2));console.log({errors});await browser.close();if(errors.length)process.exit(1);
