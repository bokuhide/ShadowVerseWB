import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
const cards=JSON.parse(fs.readFileSync('data/cards.json','utf8'));
const metadata=JSON.parse(fs.readFileSync('data/metadata.json','utf8'));
const rotation=JSON.parse(fs.readFileSync('data/rotation.json','utf8'));
const old=JSON.parse(execFileSync('git',['show','HEAD:data/cards.json'],{encoding:'utf8',maxBuffer:20e6}));
const errors=[]; const ids=new Set(); const urls=new Set();
let styles=0, unnamed=0, evolved=0; const changed=[];
for(const c of cards){
 if(ids.has(c.card_id))errors.push(`duplicate ${c.card_id}`); ids.add(c.card_id);
 for(const k of ['カード名','クラス','種類','card_set','rarity'])if(!c[k])errors.push(`missing ${k}: ${c.card_id}`);
 if(!Array.isArray(c.card_styles))errors.push(`styles not array: ${c.card_id}`);
 if(!c.image_url)errors.push(`missing base image: ${c.card_id}`);
 if(typeof c.is_include_rotation!=='boolean')errors.push(`missing rotation flag: ${c.card_id}`);
 if(!Number.isInteger(c.card_id)||!Number.isInteger(c['コスト'])||c['コスト']<0)errors.push(`invalid ID/cost: ${c.card_id}`);
 if(c['種類']==='フォロワー'?!Number.isInteger(c['攻撃'])||!Number.isInteger(c['体力']):c['攻撃']!==null||c['体力']!==null)errors.push(`invalid stats: ${c.card_id}`);
 if(c.evolved_image_url)evolved++;
 const hashes=new Set();
 for(const s of c.card_styles){styles++;if(!s.style_name)unnamed++;if(hashes.has(s.image_hash))errors.push(`duplicate style: ${c.card_id}`);hashes.add(s.image_hash);}
 for(const obj of [c,...c.card_styles])for(const k of ['image_url','evolved_image_url'])if(obj[k]){
  if(!/^https:\/\/shadowverse-wb\.com\/uploads\/card_image\/jpn\/card\/[a-f0-9]+\.png$/.test(obj[k]))errors.push(`invalid URL: ${obj[k]}`);
  urls.add(obj[k]);
 }
 const prev=old.find(x=>x.card_id===c.card_id);
 if(prev){const fields=Object.keys(prev).filter(k=>JSON.stringify(prev[k])!==JSON.stringify(c[k]));if(fields.length)changed.push({id:c.card_id,name:c['カード名'],fields});}
}
if(cards.length!==metadata.card_count||ids.size!==metadata.unique_card_id_count||styles!==metadata.card_style_count)errors.push('metadata mismatch');
const rotationIds=cards.filter(c=>c.is_include_rotation).map(c=>c.card_id);
if(rotationIds.length!==metadata.rotation_card_count||cards.length-rotationIds.length!==metadata.non_rotation_card_count||rotation.card_count!==rotationIds.length||new Set(rotation.card_ids).size!==rotationIds.length||rotationIds.some(id=>!rotation.card_ids.includes(id)))errors.push('rotation mismatch');
const sampleArg=process.argv.find(a=>a.startsWith('--image-sample='));
const sampleSize=sampleArg?Number(sampleArg.split('=')[1]):urls.size;
if(!Number.isInteger(sampleSize)||sampleSize<0)throw new Error('Invalid --image-sample');
const allUrls=[...urls];
const pending=sampleSize>=allUrls.length?allUrls:sampleSize===0?[]:Array.from({length:sampleSize},(_,i)=>allUrls[Math.floor(i*allUrls.length/sampleSize)]);
let checked=0;const failed=[];
async function worker(){while(pending.length){const url=pending.pop();try{const r=await fetch(url,{signal:AbortSignal.timeout(30000)});if(!r.ok||!r.headers.get('content-type')?.startsWith('image/'))failed.push({url,status:r.status});await r.body?.cancel();}catch(e){failed.push({url,error:e.message});}checked++;}}
await Promise.all(Array.from({length:6},worker));
const report={retrieved_at:metadata.retrieved_at,cards:cards.length,styles,unnamed_styles:unnamed,evolved_base_images:evolved,added:cards.filter(c=>!old.some(o=>o.card_id===c.card_id)).length,removed:old.filter(o=>!ids.has(o.card_id)).length,changed,images_checked:checked,failed_images:failed,errors,reference_links:cards.filter(c=>/万食のアナテマ・ララアンセム|災いの言霊・ジンジャー/.test(c['カード名'])).map(c=>({name:c['カード名'],styles:c.card_styles.map(s=>s.style_name)}))};
report.unique_ids=ids.size;
report.rotation_cards=rotationIds.length;
report.comparison_base_commit=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
report.image_validation={mode:sampleSize>=urls.size?'all':'sample',unique_image_urls:urls.size,requested_sample:sampleSize};
report.validated_at=new Date().toISOString();
fs.writeFileSync('data/validation.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
if(errors.length||failed.length)process.exitCode=1;
