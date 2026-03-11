const { chromium } = require('/usr/lib/node_modules/openclaw/node_modules/playwright-core');
const fs = require('fs');

// Read args from file (written by gen_lotto_all.py)
const { fontReg, fontBold, bgImg, data } = JSON.parse(fs.readFileSync('/tmp/lotto_card_args.json', 'utf8'));

const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@700;800&family=Charm:wght@700&display=swap" rel="stylesheet">
<style>
@font-face{font-family:'NT';src:url('data:font/ttf;base64,${fontReg}') format('truetype');font-weight:400}
@font-face{font-family:'NT';src:url('data:font/ttf;base64,${fontBold}') format('truetype');font-weight:700}
*{margin:0;padding:0;box-sizing:border-box}
body{width:560px;background:#000;font-family:'Sarabun','NT',sans-serif}

.card{width:560px;border:3px solid #c8960c;border-radius:12px;overflow:hidden;position:relative;background:#1a0800}

/* รูปตัวละครเป็น background กลืนไปกับ card */
.bg-char{
  position:absolute;
  top:0;right:0;
  width:260px;height:100%;
  background-image:url('data:image/jpeg;base64,${bgImg}');
  background-size:cover;
  background-position:center top;
  opacity:0.25;
  mask-image:linear-gradient(to left, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.3) 50%, transparent 100%);
  -webkit-mask-image:linear-gradient(to left, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.3) 50%, transparent 100%);
}

.top-bar{height:7px;background:linear-gradient(90deg,#8b0000,#ffd700,#ff8c00,#ffd700,#8b0000);position:relative;z-index:2}

/* header */
.header{padding:18px 22px 14px;position:relative;z-index:2;border-bottom:1px solid rgba(200,150,12,0.4)}
.brand{font-family:'Charm','Sarabun',sans-serif;font-size:46px;font-weight:700;color:#ffd700;line-height:1;text-shadow:0 2px 12px rgba(255,140,0,0.6),0 0 2px #000}
.brand-en{font-size:11px;color:#c8960c;letter-spacing:5px;margin-top:3px;font-weight:700}
.lotto-badge{
  display:inline-block;
  margin-top:10px;
  background:rgba(0,0,0,0.6);
  border:1px solid #c8960c;
  border-radius:20px;
  padding:4px 14px;
  font-size:14px;font-weight:800;color:#ffd700;
}
.lotto-date{font-size:11px;color:#aa7700;margin-top:3px}

/* cross + run */
.main{display:flex;gap:0;padding:16px 22px;position:relative;z-index:2;align-items:center}
.cross{position:relative;width:180px;height:180px;flex-shrink:0}
.cc{position:absolute;width:68px;height:68px;display:flex;align-items:center;justify-content:center;font-size:36px;font-weight:800;border-radius:8px;backdrop-filter:blur(2px)}
.cc.normal{background:rgba(0,0,0,0.7);border:2px solid #8b6000;color:#fff;box-shadow:0 2px 8px rgba(0,0,0,0.5)}
.cc.ctr{background:linear-gradient(135deg,rgba(180,100,0,0.9),rgba(100,50,0,0.9));border:3px solid #ffd700;color:#fff;font-size:44px;box-shadow:0 0 20px rgba(255,215,0,0.7)}
.pos-t{top:0;left:50%;transform:translateX(-50%)}
.pos-l{top:50%;left:0;transform:translateY(-50%)}
.pos-c{top:50%;left:50%;transform:translate(-50%,-50%)}
.pos-r{top:50%;right:0;transform:translateY(-50%)}
.pos-b{bottom:0;left:50%;transform:translateX(-50%)}

.run-section{flex:1;text-align:center;padding-left:16px}
.run-lbl{font-size:12px;color:#c8960c;margin-bottom:4px;font-weight:700;letter-spacing:2px}
.run-num{font-size:82px;font-weight:800;line-height:1;letter-spacing:-4px;text-shadow:0 2px 16px rgba(0,0,0,0.8)}
.r1{color:#ff1744}.rsep{color:#ffd700;margin:0 2px;font-size:60px}.r2{color:#ff9100}

/* divider */
.gold-div{height:2px;background:linear-gradient(90deg,transparent,#8b6000 15%,#ffd700 50%,#8b6000 85%,transparent);margin:0 18px;position:relative;z-index:2}

/* nums */
.nums-wrap{padding:12px 18px 16px;position:relative;z-index:2}
.sec-title{font-size:12px;font-weight:800;color:#ffd700;text-align:center;letter-spacing:3px;margin-bottom:8px;text-shadow:0 0 8px rgba(255,215,0,0.5)}
.nums2{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-bottom:12px}
.n2{
  min-width:54px;text-align:center;
  font-size:26px;font-weight:800;color:#fff;
  background:rgba(0,0,0,0.65);
  border:2px solid #c8960c;border-radius:8px;
  padding:5px 12px;
  text-shadow:0 1px 4px rgba(0,0,0,0.9);
  box-shadow:0 0 8px rgba(200,150,12,0.3);
}
.nums3{display:flex;gap:14px;justify-content:center}
.n3{font-size:28px;font-weight:800;color:#ffd700;letter-spacing:2px;text-shadow:0 0 12px rgba(255,215,0,0.7)}

.bot-bar{height:7px;background:linear-gradient(90deg,#8b0000,#ffd700,#ff8c00,#ffd700,#8b0000);position:relative;z-index:2}
</style></head><body>
<div class="card">
  <div class="bg-char"></div>
  <div class="top-bar"></div>

  <div class="header">
    <div class="brand">${data.brand}</div>
    <div class="brand-en">BAAN HUAY 888</div>
    <div class="lotto-badge">${data.lotto_name}</div>
    <div class="lotto-date">${data.date}</div>
  </div>

  <div class="main">
    <div class="cross">
      <div class="cc normal pos-t">${data.grid[0]}</div>
      <div class="cc normal pos-l">${data.grid[1]}</div>
      <div class="cc ctr pos-c">${data.grid[2]}</div>
      <div class="cc normal pos-r">${data.grid[3]}</div>
      <div class="cc normal pos-b">${data.grid[4]}</div>
    </div>
    <div class="run-section">
      <div class="run-lbl">วิ่ง / รูด</div>
      <div class="run-num"><span class="r1">${data.run1}</span><span class="rsep">-</span><span class="r2">${data.run2}</span></div>
    </div>
  </div>

  <div class="gold-div"></div>
  <div class="nums-wrap">
    <div class="sec-title">-- เลข 2 ตัวล่าง --</div>
    <div class="nums2">${data.nums2.map(n=>`<span class="n2">${n}</span>`).join('')}</div>
    <div class="sec-title">-- เลข 3 ตัวบน --</div>
    <div class="nums3">${data.nums3.map(n=>`<span class="n3">${n}</span>`).join('  ')}</div>
  </div>
  <div class="bot-bar"></div>
</div></body></html>`;

(async()=>{
  const b = await chromium.launch({headless:true,args:['--no-sandbox','--disable-gpu']});
  const ctx = await b.newContext({deviceScaleFactor:2});
  const p = await ctx.newPage();
  await p.setViewportSize({width:560,height:620});
  await p.setContent(html,{waitUntil:'networkidle'});
  await p.waitForTimeout(800);
  const el = await p.$('.card');
  await el.screenshot({path:data.output});
  await b.close();
  console.log('done');
})();
