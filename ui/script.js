const bg = document.getElementById('bg');
const wave = document.getElementById('wave');
const micStatus = document.getElementById('mic-status');
const procStatus = document.getElementById('proc-status');
const sysStatus = document.getElementById('sys-status');
const micText = document.getElementById('mic-text');
const procText = document.getElementById('proc-text');
const sysText = document.getElementById('sys-text');

// Background particles
const bgCtx = bg.getContext('2d');
let particles = [];
function resizeBg(){
  bg.width = innerWidth; bg.height = innerHeight;
  particles = Array.from({length: 120}, ()=>({
    x: Math.random()*bg.width,
    y: Math.random()*bg.height,
    r: Math.random()*1.8+0.2,
    vx: (Math.random()-0.5)*0.2,
    vy: (Math.random()-0.5)*0.2,
    c: Math.random()<0.5? '#00ffff':'#ff00ff'
  }));
}
resizeBg();
addEventListener('resize', resizeBg);

function drawBg(){
  bgCtx.clearRect(0,0,bg.width,bg.height);
  for(const p of particles){
    p.x+=p.vx; p.y+=p.vy;
    if(p.x<0||p.x>bg.width) p.vx*=-1;
    if(p.y<0||p.y>bg.height) p.vy*=-1;
    bgCtx.beginPath();
    bgCtx.arc(p.x,p.y,p.r,0,Math.PI*2);
    bgCtx.fillStyle=p.c;
    bgCtx.globalAlpha=0.6;
    bgCtx.shadowBlur=8; bgCtx.shadowColor=p.c;
    bgCtx.fill();
    bgCtx.globalAlpha=1;
  }
  requestAnimationFrame(drawBg);
}
drawBg();

// Waveform ring
const wCtx = wave.getContext('2d');
function resizeWave(){
  const rect = wave.getBoundingClientRect();
  wave.width = rect.width*devicePixelRatio;
  wave.height = rect.height*devicePixelRatio;
}
resizeWave();
addEventListener('resize', resizeWave);

let level = 0.0; // 0..1
function drawWave(){
  const cx = wave.width/2, cy = wave.height/2;
  const radius = Math.min(cx, cy) - 6*devicePixelRatio;
  wCtx.clearRect(0,0,wave.width,wave.height);
  // base circle
  wCtx.beginPath();
  wCtx.arc(cx,cy,radius,0,Math.PI*2);
  wCtx.strokeStyle='rgba(255,255,255,0.08)';
  wCtx.lineWidth=2*devicePixelRatio;
  wCtx.stroke();
  // waveform arc
  const amp = 0.2 + level*0.8;
  const segs = 120;
  for(let i=0;i<segs;i++){
    const t = i/segs; // 0..1
    const ang = t*Math.PI*2;
    const wobble = Math.sin((t+performance.now()/1200)*Math.PI*2)*amp*2;
    const rr = radius - 8*devicePixelRatio + wobble*devicePixelRatio;
    const x = cx + Math.cos(ang)*rr;
    const y = cy + Math.sin(ang)*rr;
    const hue = t*360;
    wCtx.fillStyle = `hsl(${hue}, 100%, ${40+amp*20}%)`;
    wCtx.shadowBlur=8; wCtx.shadowColor = level>0.4? '#ff00ff':'#00ffff';
    wCtx.beginPath(); wCtx.arc(x,y,1.8*devicePixelRatio,0,Math.PI*2); wCtx.fill();
  }
  requestAnimationFrame(drawWave);
}
drawWave();

// Poll status
async function poll(){
  try{
    const res = await fetch('/api/status');
    const j = await res.json();
    setStatus(j);
  }catch(e){/* ignore */}
  setTimeout(poll, 800);
}
poll();

function setStatus(s){
  level = Math.max(0, Math.min(1, s.level ?? level));
  // mic
  micText.textContent = s.mic === 'listening' ? 'Listening' : 'Idle';
  micStatus.querySelector('.dot').style.color = s.mic==='listening' ? '#00ffff' : '#555';
  // processing
  procText.textContent = s.processing ? 'Processing…' : 'Standby';
  procStatus.querySelector('.dot').style.color = s.processing ? '#ff00ff' : '#555';
  // system
  sysText.textContent = (s.system||'ok').toUpperCase();
  const col = s.system==='ok' ? '#00e676' : (s.system==='busy' ? '#ffea00' : '#ff5252');
  sysStatus.querySelector('.dot').style.color = col;
}


// Command submit
const form = document.getElementById('cmd-form');
const input = document.getElementById('cmd-input');
const result = document.getElementById('cmd-result');
if(form){
  form.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const text = (input?.value||'').trim();
    if(!text) return;
    result.textContent = 'Running…';
    try{
      const res = await fetch('/api/command', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({text})
      });
      const j = await res.json().catch(()=>({ok:false}));
      if(j.ok){
        result.textContent = 'Done';
        input.value = '';
      }else{
        result.textContent = 'Error';
      }
    }catch(err){
      result.textContent = 'Network error';
    }
  });
}
