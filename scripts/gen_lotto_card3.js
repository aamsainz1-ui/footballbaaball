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
.round-title{font-size:13px;font-weight:700;color:#d1a0e0}
.round-body{padding:14px 20px;background:#0d0d20}

.hot-row{display:flex;gap:10px;margin-bottom:12px}
.hot-box{flex:1;background:linear-gradient(135deg,#4a0072,#2d0050);border:2px solid #e040fb;border-radius:10px;padding:10px;text-align:center;box-shadow:0 0 12px rgba(224,64,251,0.25)}
.hot-label{font-size:9px;color:#e040fb;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}
.hot-val{font-size:30px;font-weight:700;color:#fff;line-height:1}
.hot-sub{font-size:9px;color:#9c6aaa;margin-top:2px}

.num-group{margin-bottom:10px}
.num-label{font-size:10px;color:#8866aa;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.nums-wrap{display:flex;flex-wrap:wrap;gap:6px}
.num-pill{background:rgba(44,0,80,0.8);border:1px solid #7b1fa2;border-radius:7px;padding:5px 13px;font-size:18px;font-weight:700;color:#ddd;letter-spacing:2px}
.num-pill.first{border-color:#ce93d8;color:#fff}
.run-wrap{display:flex;gap:8px}
.run-pill{background:linear-gradient(135deg,#1a0533,#2d0050);border:1px solid #9c27b0;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;color:#e040fb}

.footer{background:#06060f;padding:12px 24px;text-align:center;border-top:1px solid rgba(255,255,255,0.04)}
.footer-text{font-size:10px;color:#333}
.warn{font-size:10px;color:#4a2a5a;margin-top:2px}
</style></head>
<body><div class="card">
<div class="header">
  <div><div class="brand">บ้านหวย888</div><div class="sub">เลขเด็ดประจำวัน</div></div>
  <div class="date-badge">${data.date}<br>${data.lotto_date}</div>
</div>
${data.rounds.map((r,i) => `
<div class="round">
  <div class="round-header">
    <span class="round-num">รอบ ${i+1}</span>
    <span class="round-title">${r.title}</span>
  </div>
  <div class="round-body">
    <div class="hot-row">
      ${r.hot3 ? `<div class="hot-box"><div class="hot-label">3 ตัวเด่น</div><div class="hot-val">${r.hot3}</div><div class="hot-sub">HOT</div></div>` : ''}
      ${r.hot2 ? `<div class="hot-box"><div class="hot-label">2 ตัวเด่น</div><div class="hot-val">${r.hot2}</div><div class="hot-sub">HOT</div></div>` : ''}
      ${r.run ? `<div class="hot-box" style="flex:0.5"><div class="hot-label">วิ่ง</div><div class="hot-val">${r.run}</div><div class="hot-sub">เด่น</div></div>` : ''}
    </div>
    ${r.nums3 && r.nums3.length ? `<div class="num-group"><div class="num-label">3 ตัวบน</div><div class="nums-wrap">${r.nums3.map((n,ni)=>`<div class="num-pill${ni===0?' first':''}">${n}</div>`).join('')}</div></div>` : ''}
    ${r.nums2 && r.nums2.length ? `<div class="num-group"><div class="num-label">2 ตัวล่าง</div><div class="nums-wrap">${r.nums2.map((n,ni)=>`<div class="num-pill${ni===0?' first':''}">${n}</div>`).join('')}</div></div>` : ''}
    ${r.runs && r.runs.length ? `<div class="num-group"><div class="num-label">วิ่งบน</div><div class="run-wrap">${r.runs.map(n=>`<div class="run-pill">${n}</div>`).join('')}</div></div>` : ''}
  </div>
</div>`).join('')}
<div class="footer">
  <div class="footer-text">บ้านหวย888 · คำนวณจากสูตรและสถิติย้อนหลัง</div>
  <div class="warn">เล่นอย่างมีสติ รับผิดชอบตัวเอง</div>
</div>
</div></body></html>`;

(async () => {
  const b = await chromium.launch({headless:true, args:['--no-sandbox','--disable-gpu']});
  const p = await b.newPage();
  await p.setViewportSize({width:540, height:1400});
  await p.setContent(html, {waitUntil:'load'});
  await p.waitForTimeout(300);
  const el = await p.$('.card');
  await el.screenshot({path: data.output});
  await b.close();
  console.log('done');
})();
