const { chromium } = require('/usr/lib/node_modules/openclaw/node_modules/playwright-core');
const [fontReg, fontBold, jsonArg] = process.argv.slice(2);
const data = JSON.parse(jsonArg);

const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
@font-face{font-family:'NT';src:url('data:font/ttf;base64,${fontReg}') format('truetype');font-weight:400}
@font-face{font-family:'NT';src:url('data:font/ttf;base64,${fontBold}') format('truetype');font-weight:700}
*{margin:0;padding:0;box-sizing:border-box}
body{width:540px;font-family:'NT',sans-serif;background:#08080f}
.card{background:#0c0c1e;overflow:hidden}

.header{background:linear-gradient(135deg,#1a0533,#3d0066,#1a0533);padding:20px 24px;border-bottom:3px solid #bf00ff;display:flex;justify-content:space-between;align-items:center}
.brand{font-size:26px;font-weight:700;color:#e040fb;letter-spacing:2px}
.sub{font-size:11px;color:#9c6aaa;margin-top:3px}
.date-badge{background:rgba(224,64,251,0.12);border:1px solid rgba(224,64,251,0.35);color:#e040fb;font-size:11px;font-weight:700;padding:6px 14px;border-radius:6px;text-align:center}

.round{border-bottom:1px solid rgba(255,255,255,0.06)}
.round-header{background:rgba(224,64,251,0.08);border-left:3px solid #9c27b0;padding:10px 20px;display:flex;align-items:center;gap:8px}
.round-num{background:#9c27b0;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:3px;letter-spacing:1px}
.round-title{font-size:12px;font-weight:700;color:#d1a0e0}

.round-body{padding:12px 20px 14px;background:#0d0d20}
.num-group{margin-bottom:8px}
.num-label{font-size:10px;color:#8866aa;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.nums-wrap{display:flex;flex-wrap:wrap;gap:6px}
.num-pill{background:linear-gradient(135deg,#2d0050,#1a003a);border:1px solid #9c27b0;border-radius:8px;padding:6px 14px;font-size:20px;font-weight:700;color:#fff;letter-spacing:2px}
.num-pill.hot{border-color:#e040fb;color:#e040fb;box-shadow:0 0 8px rgba(224,64,251,0.3)}

.footer{background:#06060f;padding:12px 24px;text-align:center;border-top:1px solid rgba(255,255,255,0.04)}
.footer-text{font-size:10px;color:#333}
.warn{font-size:10px;color:#6a3a7a;margin-top:2px}
</style></head>
<body><div class="card">

<div class="header">
  <div><div class="brand">บ้านหวย888</div><div class="sub">เลขเด็ดประจำวัน</div></div>
  <div class="date-badge">${data.date}<br>${data.lotto_date}</div>
</div>

${data.rounds.map((r,i) => `
<div class="round">
  <div class="round-header">
    <span class="round-num">รอบที่ ${i+1}</span>
    <span class="round-title">${r.title}</span>
  </div>
  <div class="round-body">
    ${r.groups.map(g => `
    <div class="num-group">
      <div class="num-label">${g.label}</div>
      <div class="nums-wrap">
        ${g.nums.map((n,ni) => `<div class="num-pill${ni===0?' hot':''}">${n}</div>`).join('')}
      </div>
    </div>`).join('')}
  </div>
</div>`).join('')}

<div class="footer">
  <div class="footer-text">บ้านหวย888 · เลขคำนวณจากสูตร</div>
  <div class="warn">เล่นอย่างมีสติ รับผิดชอบตัวเอง</div>
</div>
</div></body></html>`;

(async () => {
  const b = await chromium.launch({headless:true, args:['--no-sandbox','--disable-gpu']});
  const p = await b.newPage();
  await p.setViewportSize({width:540, height:1200});
  await p.setContent(html, {waitUntil:'load'});
  await p.waitForTimeout(300);
  const el = await p.$('.card');
  await el.screenshot({path: data.output});
  await b.close();
  console.log('done');
})();
