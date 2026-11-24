const EDGES=[[0,1],[0,2],[1,3],[2,4],[0,5],[0,6],[5,7],[7,9],[6,8],[8,10],[5,6],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16]];
const $=id=>document.getElementById(id),canvas=$('stage'),ctx=canvas.getContext('2d');
let frames=[],segments=[],frameIndex=0,selectedSegment=-1,timer=null;
const naturalLabel=label=>({walking:'걷는 모습',walking_run:'걷거나 달리는 모습',running:'달리는 모습',standing:'서 있는 모습',turning_head:'고개를 돌리는 모습',pushing_skateboard:'도구를 미는 모습',sitting:'앉은 모습',lying_sleeping:'누워 쉬는 모습',eating_drinking:'먹거나 마시는 모습'}[label]||`${label} 참고 모습`);
function fuzzyName(key){return ({low:'낮음',moderate:'보통',high:'높음',LOW:'낮음',MODERATE:'보통',HIGH:'높음'}[key]||key).replace('POSE_OBSERVABILITY_','')}
function bestMembership(f){return Object.entries(f.memberships||{}).sort((a,b)=>b[1]-a[1])[0]||['-',0]}
function renderGraph(){const root=$('observationGraph');if(!root||!segments.length)return;root.innerHTML='<strong>구간별 결합 결과 — 관절 계측 → Fuzzy 보조평가 → CLIP 매칭</strong>'+segments.map((s,n)=>{const p=s.pose_observation,c=p.valid_joint_ratio*100,[fk,fv]=bestMembership(s.fuzzy_observation),hit=s.clip_reference_hits?.[0];return `<button class="graph-row${n===selectedSegment?' active':''}" data-index="${n}"><span>${s.segment_id}</span><span class="joint-bar"><i style="width:${Math.min(100,c)}%"></i></span><em>관절 ${value(c,1)}% → Fuzzy ${fuzzyName(fk)} ${value(fv,3)} → ${hit?`${naturalLabel(hit.reference_label)} ${value(hit.similarity,3)}`:'CLIP 미표본'}</em></button>`}).join('');root.querySelectorAll('.graph-row').forEach(b=>b.onclick=()=>renderSegment(+b.dataset.index,true))}
function poseSvg(thumbnail){if(!thumbnail?.coordinates)return '<p>QUERY_POSE_UNAVAILABLE</p>';const points=thumbnail.coordinates,lines=EDGES.map(([a,b])=>points[a]?.x!=null&&points[b]?.x!=null?`<line x1="${10+points[a].x*180}" y1="${10+points[a].y*120}" x2="${10+points[b].x*180}" y2="${10+points[b].y*120}"/>`:``).join(''),dots=points.map(p=>p?.x!=null?`<circle cx="${10+p.x*180}" cy="${10+p.y*120}" r="3"/>`:``).join('');return `<svg class="pose-card" viewBox="0 0 200 140" role="img" aria-label="실제 구간 쿼리 포즈 스켈레톤"><g>${lines}${dots}</g></svg><p class="muted">${thumbnail.authority} · ${thumbnail.schema} · reference pose가 아님</p>`}

function segmentForFrame(index){return segments.findIndex(s=>index>=s.frame_start&&index<=s.frame_end)}
function value(v,digits=4){return v==null?'null':Number(v).toFixed(digits)}
function renderSegment(index,seek=false){
  if(index<0||index>=segments.length)return;
  selectedSegment=index;
  const s=segments[index],p=s.pose_observation,f=s.fuzzy_observation;
  document.querySelectorAll('#timeline button').forEach((b,n)=>b.classList.toggle('active',n===index));
  if(seek){frameIndex=Math.max(0,frames.findIndex(x=>x.frame_index>=s.frame_start));draw()}
  $('segmentId').textContent=`${s.segment_id} · frames ${s.frame_start}–${s.frame_end}`;
  const topHit=s.clip_reference_hits?.[0],publicHit=s.public_cc0_image_matches?.[0],[bestKey,bestValue]=bestMembership(f);
  $('decisionFlow').innerHTML=`<div><small>1 · 포즈 관측</small><b>관절 ${value(p.valid_joint_ratio*100,1)}%</b></div><span>→</span><div><small>2 · Fuzzy 보조평가</small><b>${fuzzyName(bestKey)} ${value(bestValue,3)}</b></div><span>→</span><div><small>3 · CLIP 자연어 매칭</small><b>${topHit?`${naturalLabel(topHit.reference_label)} ${value(topHit.similarity,3)}`:'미표본'}</b></div><span>→</span><div><small>4 · 공개 이미지</small><b>${publicHit?`${publicHit.asset_id} ${value(publicHit.cosine_similarity,3)}`:'미표본'}</b></div>`;
  $('poseEvidence').innerHTML=poseSvg(p.query_pose_thumbnail)+`<p>유효 관절 비율 <b>${value(p.valid_joint_ratio,3)}</b></p><div class="meter"><i style="width:${Math.min(100,p.valid_joint_ratio*100)}%"></i></div><details><summary>계측 제한</summary><p class="muted">프레임 간 동일 개체 추적을 주장하지 않아 속도·변위는 산출하지 않습니다.</p></details>`;
  const memberships=Object.entries(f.memberships||{}).map(([k,v])=>`<div class="membership"><span>${fuzzyName(k)}</span><i style="width:${Math.min(100,v*100)}%"></i><b>${value(v,3)}</b></div>`).join('');
  $('fuzzyEvidence').innerHTML=`<strong>${fuzzyName(bestKey)} 관측 소속도가 가장 높음 · ${value(bestValue,3)}</strong><div class="membership-list">${memberships}</div><p>${f.explanation_text}</p><p class="muted">${f.rule_version} · 소속도는 행동 확률이 아닌 보조평가입니다.</p>`;
  const research=(s.clip_reference_hits||[]).map(h=>`<div class="hit">추천 ${h.rank} · ${naturalLabel(h.reference_label)}과 유사 · cosine ${value(h.similarity,3)}</div>`).join('');
  const publicImages=(s.public_cc0_image_matches||[]).map(h=>`<div class="public-hit"><img src="${h.public_image_url}" alt="${h.asset_id} CC0 참고 이미지"><span>#${h.rank} ${h.asset_id} · cosine ${value(h.cosine_similarity,3)} · ${h.license}</span></div>`).join('');
  $('clipEvidence').innerHTML=`<strong>실제 RN50 코사인 유사도 매칭</strong><p>${research||'연구 참고 사례 미표본'}</p><p><b>CC0 공개 이미지 Top-3</b></p>${publicImages||'<p>공개 이미지 미표본</p>'}<p class="muted">값이 클수록 임베딩이 가까운 참고 사례입니다. 행동 확률이나 확정 판정은 아닙니다.</p>`;
  $('reviewSummary').innerHTML=`<b>제한적 전문가 보조 추천</b><br>${s.review_assistance||`${s.segment_id}의 포즈 관측·Fuzzy 소속도·CLIP 코사인 유사도를 함께 검토합니다.`}`;renderGraph();
}
function draw(){
  const f=frames[frameIndex];if(!f)return;
  ctx.clearRect(0,0,canvas.width,canvas.height);const sx=canvas.width/f.source_width,sy=canvas.height/f.source_height,pts=f.keypoints;
  ctx.lineWidth=4;ctx.strokeStyle='#50e3b1';
  for(const [a,b] of EDGES){if(!pts[a]||!pts[b]||pts[a].confidence<.12||pts[b].confidence<.12)continue;ctx.beginPath();ctx.moveTo(pts[a].x*sx,pts[a].y*sy);ctx.lineTo(pts[b].x*sx,pts[b].y*sy);ctx.stroke()}
  for(const p of pts){if(p.confidence<.12)continue;ctx.fillStyle=p.confidence<.3?'#ffbf69':'#eafcff';ctx.beginPath();ctx.arc(p.x*sx,p.y*sy,p.confidence<.3?4:6,0,Math.PI*2);ctx.fill()}
  $('seek').value=frameIndex;$('frame').value=`${frameIndex+1} / ${frames.length}`;$('state').textContent=`FRAME_ORDER_ONLY · AP10K_NATIVE17 · frame ${f.frame_index} · 실제 관측 confidence 보존`;
  const segmentIndex=segmentForFrame(f.frame_index);if(segmentIndex>=0&&segmentIndex!==selectedSegment)renderSegment(segmentIndex,false);
}
function play(){if(timer||!frames.length)return;timer=setInterval(()=>{frameIndex=(frameIndex+1)%frames.length;draw()},1000/15)}
function pause(){clearInterval(timer);timer=null}
function buildTimeline(){const root=$('timeline');root.textContent='';segments.forEach((s,index)=>{const b=document.createElement('button');b.type='button';b.textContent=`${s.segment_id} · ${s.frame_start}–${s.frame_end}`;b.onclick=()=>renderSegment(index,true);root.append(b)})}
$('play').onclick=play;$('pause').onclick=pause;$('restart').onclick=()=>{pause();frameIndex=0;draw()};$('seek').oninput=e=>{pause();frameIndex=+e.target.value;draw()};$('demoCta').onclick=()=>{$('demo').scrollIntoView({behavior:'smooth'});play()};
document.addEventListener('keydown',e=>{if(e.code==='Space'){e.preventDefault();timer?pause():play()}if(e.code==='Home')$('restart').click()});
Promise.all([
  fetch('samples/demo-walking-001/pose-frames.json').then(r=>{if(!r.ok)throw Error(`pose ${r.status}`);return r.json()}),
  fetch('samples/demo-walking-001/segments.json').then(r=>{if(!r.ok)throw Error(`segments ${r.status}`);return r.json()})
]).then(([pose,data])=>{frames=pose.frames;segments=data.segments;$('seek').max=frames.length-1;buildTimeline();draw()}).catch(e=>$('state').textContent=`STATIC_ASSET_ERROR · ${e.message}`);
