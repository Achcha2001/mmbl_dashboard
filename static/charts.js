let dailyChart=null, districtChart=null;
async function loadSummary(){
  const r=await fetch('/api/summary'), d=await r.json();
  drawDailyChart(d.daily_counts);
  drawDistrictChart(d.district_decline);
  populateRepTable(d.rep_counts, d.visit_info);
}
document.getElementById('upload-form')?.addEventListener('submit',async e=>{
  e.preventDefault();
  const f=new FormData(e.target);
  const res=await fetch('/upload',{method:'POST',body:f});
  if(res.ok)loadSummary();
});
function drawDailyChart(data){
  const ctx=document.getElementById('daily-chart')?.getContext('2d');
  if(!ctx)return;
  if(dailyChart)dailyChart.destroy();
  dailyChart=new Chart(ctx,{type:'line',data:{labels:Object.keys(data),datasets:[{label:'Txns/Day',data:Object.values(data),fill:false,tension:0.1}]},options:{scales:{y:{beginAtZero:true}}}});
}
function drawDistrictChart(data){
  const first=Object.values(data)[0]||{},dates=Object.keys(first),latest=dates.at(-1);
  const labels=[],vals=[];
  for(const [k,m] of Object.entries(data)){labels.push(k);vals.push(m[latest]||0);}
  const ctx=document.getElementById('district-chart')?.getContext('2d');
  if(!ctx)return;
  if(districtChart)districtChart.destroy();
  districtChart=new Chart(ctx,{type:'bar',data:{labels, datasets:[{label:`% Change ${latest}`,data:vals}]},options:{scales:{y:{beginAtZero:true}}}});
}
function populateRepTable(cnts,vis){
  const tb=document.querySelector('#rep-table tbody'); if(!tb) return; tb.innerHTML='';
  for(const [r,c] of Object.entries(cnts)){
    const v=vis[r]||{},f=v.first||'',l=v.last||'';
    tb.insertAdjacentHTML('beforeend',`<tr><td>${r}</td><td>${c}</td><td>${f}</td><td>${l}</td></tr>`);
  }
}
window.addEventListener('DOMContentLoaded',loadSummary);
