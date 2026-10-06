#!/usr/bin/env node
/* حزام إتاحة الحوارات — ورقة الجوال `#sheet` ودرج التفاصيل `#drawer`.
 *
 * لماذا متصفّح: الحوار المغلق في هذه الصفحة مُزاح بـ`transform` وحده — لا
 * `display:none` ولا `visibility:hidden` — فسؤالُ «هل يلمسه التركيز؟» سؤالٌ عن شجرة
 * تنقّل المتصفح لا عن نصّ الملف، ولا يُجاب إلا بقياس. ولذلك يعيش هذا الملف في
 * `tests/browser/` وحده: الحزامات في `tests/` بلا تبعية، وهذا يحتاج Playwright
 * وChromium وخادماً محلياً — انظر `tests/browser/README.md`.
 *
 * تخطٍّ رحيم: إن لم يُحلَّ `playwright` يطبع ⊘ ويخرج 0 — تخطٍّ لا يُقرأ نجاحاً.
 *
 * الاستخدام: node tests/browser/a11y-sheet.mjs [اسم-الملف]     (الافتراضي uat.html)
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const ROOT = path.dirname(path.dirname(path.dirname(fileURLToPath(import.meta.url))));
const PAGE = process.argv[2] || "uat.html";

/* ── حلّ playwright: المحلّي، ثم الجذر العام لـnpm ── */
async function loadPlaywright(){
  const pick = m => (m && m.chromium) ? m : (m && m.default && m.default.chromium ? m.default : null);
  try { const m = pick(await import("playwright")); if (m) return m; } catch {}
  try {
    const g = execSync("npm root -g", { encoding:"utf8", stdio:["ignore","pipe","ignore"] }).trim();
    const m = pick(await import(path.join(g, "playwright", "index.js"))); if (m) return m;
  } catch {}
  return null;
}
const pw = await loadPlaywright();
if (!pw) {
  console.log("⊘ تُخطّي: playwright غير متاح — لا قياس (والتخطّي ليس نجاحاً)");
  process.exit(0);
}

/* ── خادم ساكن بلا تبعية: الصفحة تقرأ stocks-data.json بـfetch ── */
const MIME = { ".html":"text/html; charset=utf-8", ".json":"application/json; charset=utf-8",
               ".js":"text/javascript; charset=utf-8", ".css":"text/css; charset=utf-8",
               ".svg":"image/svg+xml", ".ico":"image/x-icon" };
const server = http.createServer((req,res)=>{
  const rel = decodeURIComponent(req.url.split("?")[0]).replace(/^\/+/,"") || PAGE;
  const abs = path.join(ROOT, rel);
  if (!abs.startsWith(ROOT) || !fs.existsSync(abs) || fs.statSync(abs).isDirectory()){
    res.writeHead(404); return res.end("404");
  }
  res.writeHead(200, { "Content-Type": MIME[path.extname(abs)] || "application/octet-stream" });
  fs.createReadStream(abs).pipe(res);
});
await new Promise(r=>server.listen(0,"127.0.0.1",r));
const BASE = `http://127.0.0.1:${server.address().port}`;

let pass=0, fail=0;
const ok=(cond,label,got)=>{ if(cond){pass++;} else {fail++;
  console.log(`  ❌ ${label}`+(got!==undefined?`\n     وجد: ${JSON.stringify(got)}`:"")); } };

const browser = await pw.chromium.launch();

/* ═════════════ أدوات على صفحة ═════════════ */
function tools(page){
  const where = () => page.evaluate(()=>{
    const a=document.activeElement;
    if(!a) return null;
    return { id:a.id||null, cls:a.className||null, tag:a.tagName, body:a===document.body,
             sym:a.getAttribute?a.getAttribute("data-sym"):null,
             inSheet:!!a.closest("#sheet"), inDrawer:!!a.closest("#drawer") };
  });
  const attrs = sel => page.evaluate(s=>{
    const el=document.querySelector(s); if(!el) return null;
    return { inert:el.hasAttribute("inert"), ariaHidden:el.getAttribute("aria-hidden"),
             open:el.classList.contains("open") };
  }, sel);
  /* قابلية التركيز المباشرة: عنصرٌ في شجرة inert لا يستقبل التركيز مهما نودِي */
  const reachableInside = sel => page.evaluate(s=>{
    const host=document.querySelector(s); if(!host) return {count:0, reachable:[]};
    const cands=[...host.querySelectorAll('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])')];
    const reachable=[]; const prev=document.activeElement;
    for(const el of cands){ try{ el.focus(); }catch{} if(document.activeElement===el) reachable.push(el.id||el.className||el.tagName); }
    try{ prev&&prev.focus&&prev.focus(); }catch{}
    return { count:cands.length, reachable };
  }, sel);
  /* مسحٌ من رأس الصفحة حتى آخرها — ورأسُها عنصرٌ موسوم لا `blur()`: ‏blur() لا يُصفّر
     «نقطةَ بدء التنقّل التسلسلي» في Chromium، فكان كل مسحٍ يُكمل من حيث تركه السابق.
     **ويُحرَس البدءُ بتأكيدٍ صريح (startedAt)**: كشفُ تمام الدورة بالهوية يستوفي
     الحلقةَ من أي نقطةِ بدء، فـreachedEnd يحرس «استيفاء الدورة» لا «البدء من الرأس» —
     وبلا حارسٍ على البدء كان إرجاعُ blur() يمرّ صامتاً (برهنه ختمُ المراجعة بطفرة).
     وكشفُ التمام بالهوية لا بالتوقيع لأن مئات البطاقات تتشابه توقيعاً، فالمقارنةُ
     النصّية كانت تُعلن الدورة تامّةً بعد ثلاث خطوات.
     وتعيينُ الطرفين بالوقوع لا بـoffsetParent: الأخيرُ يكذب على كل عنصر
     position:fixed — وهو الاستدلالُ نفسه الذي أسقطه restoreFocus. */
  const markEnds = () => page.evaluate(()=>{
    const SEL='a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])';
    const all=[...document.querySelectorAll(SEL)]
      .filter(el=>!el.closest("#sheet")&&!el.closest("#drawer")&&!el.closest("#tip"));
    const can=el=>{ try{ el.focus(); }catch(e){ return false; } return document.activeElement===el; };
    document.querySelectorAll("[data-sw]").forEach(el=>el.removeAttribute("data-sw"));
    let a=null,b=null;
    for(let i=0;i<all.length&&!a;i++) if(can(all[i])) a=all[i];
    for(let i=all.length-1;i>=0&&!b;i--) if(can(all[i])) b=all[i];
    if(!a||!b||a===b) return 0;
    a.setAttribute("data-sw","first"); b.setAttribute("data-sw","last");
    /* يُرجَع عددُ ما يقع فعلاً لا العدُّ الخام: الخامُ 1205 والواقعُ ~596، ولافتةُ
       التأكيد تقول «مرشّحو المسح» فتُقاس بما تعني. */
    return all.filter(can).length;
  });
  async function tabSweep(back=false, cap=4000){
    const n = await markEnds();
    const from = back ? "last" : "first", to = back ? "first" : "last";
    await page.focus(`[data-sw="${from}"]`);
    const startedAt = await page.evaluate(()=>{
      const a=document.activeElement;
      window.__swFirst=null;
      return a && a.getAttribute ? a.getAttribute("data-sw") : null;
    });
    const hits=[]; let steps=0, reachedEnd=false;
    for(let i=0;i<cap;i++){
      await page.keyboard.press(back?"Shift+Tab":"Tab"); steps++;
      const st=await page.evaluate(t=>{
        const a=document.activeElement;
        if(!a||a===document.body) return { end:true };
        if(window.__swFirst===null) window.__swFirst=a;
        else if(window.__swFirst===a) return { end:true };
        return { end:false, id:a.id||null, cls:a.className||null, tag:a.tagName,
                 atEnd:a.getAttribute("data-sw")===t,
                 inSheet:!!a.closest("#sheet"), inDrawer:!!a.closest("#drawer") };
      }, to);
      if(st.end) break;
      if(st.atEnd) reachedEnd=true;
      if(st.inSheet||st.inDrawer) hits.push(st);
    }
    return { steps, hits, reachedEnd, startedAt, expectStart:from, candidates:n };
  }
  async function ensureClosed(){
    for(const sel of ["#sheet","#drawer"]){
      if(await page.evaluate(s=>document.querySelector(s).classList.contains("open"), sel)){
        await page.keyboard.press("Escape");
        await page.waitForFunction(s=>!document.querySelector(s).classList.contains("open"), sel);
      }
    }
    await page.waitForTimeout(260);
  }
  return { where, attrs, reachableInside, tabSweep, ensureClosed };
}

async function openPage(width,height){
  const ctx = await browser.newContext({ viewport:{width,height}, locale:"ar-SA" });
  const page = await ctx.newPage();
  /* فصلُ أخطاء الصفحة عن طلباتٍ خارجيةٍ محجوبة: `index.html` المبني يحمل عدّاد
     الزيارات (gc.zgo.at)، فيعطي 403 في بيئةٍ بلا شبكة — وذلك ليس خطأ JS في الصفحة.
     يُسجَّل ولا يُفشل، والتصنيف بمصدر الرسالة لا بنصّها كي لا يُخفى فشلٌ حقيقي. */
  const errs=[], ext=[];
  page.on("pageerror", e=>errs.push("pageerror: "+e.message));
  page.on("console", m=>{
    if(m.type()!=="error") return;
    const u=(m.location()&&m.location().url)||"";
    if(u && !u.startsWith(BASE)) ext.push(u);
    else errs.push("console.error: "+m.text());
  });
  await page.goto(`${BASE}/${PAGE}`, { waitUntil:"domcontentloaded" });
  /* STOCKS و state و draft تعريفاتُ let عُلوية: ليست خواصَّ على window بل روابطُ
     المجال المعجمي العام — فتُقرأ باسمها المجرَّد داخل evaluate لا عبر window. */
  await page.waitForFunction(()=>typeof STOCKS!=="undefined" && STOCKS.length>0);
  /* البطاقات مخفية فوق 768px والجدول مخفي تحتها — فالانتظار على الإسناد لا الظهور */
  await page.waitForSelector("[data-sym]", { state:"attached" });
  return { ctx, page, errs, ext, ...tools(page) };
}

/* ════════════════════════ ١) الجوال 390×844 ════════════════════════ */
console.log("── إتاحة الحوارات على 390×844 ──");
{
const { ctx, page, errs, ext, where, attrs, reachableInside, tabSweep, ensureClosed } = await openPage(390,844);

/* حالة المولد: قبل أي تفاعل */
for(const [sel,lbl] of [["#sheet","#sheet"],["#drawer","#drawer"]]){
  const a=await attrs(sel);
  ok(a && a.inert && a.ariaHidden==="true", `١ ${lbl} يبدأ خارج الشجرتين (inert + aria-hidden)`, a);
}
const ov0=await attrs("#ovl");
ok(ov0 && ov0.ariaHidden==="true" && ov0.inert===false,
   "١ج ‏#ovl يُعلَن aria-hidden أبداً ولا inert قطّ (يحجب النقر فيكسر الإغلاق بالطبقة)", ov0);

/* دورة فتح/إغلاق — فالوسم فارغ قبلها فلا عَرَض يُقاس */
await page.click("#fabFilters"); await page.waitForSelector("#sheet.open");
const shOpen=await attrs("#sheet");
ok(shOpen && !shOpen.inert && shOpen.ariaHidden===null,
   "٢أ الفتح يرفع inert وaria-hidden معاً (وإلا فحوارٌ مفتوح أعمى على قارئ الشاشة)", shOpen);
const opened=await where();
ok(opened && opened.inSheet, "٢ب الفتح ⇒ التركيز داخل #sheet", opened);

/* حصر Tab داخل الورقة المفتوحة — الاتجاهان */
let escaped=null;
for(const back of [false,true]){
  let out=false;
  for(let i=0;i<40;i++){ await page.keyboard.press(back?"Shift+Tab":"Tab");
    const w=await where(); if(!w||!w.inSheet){ out=true; break; } }
  if(out) escaped=back?"Shift+Tab":"Tab";
}
ok(escaped===null, "٢ج ‏Tab وShift+Tab محصوران داخل الورقة المفتوحة (aria-modal يفي بما يعلن)", escaped);

/* «إعادة تعيين» تُعيد بناء الورقة — والحاصر معالجٌ على #sheet فلا يُنفَّذ والتركيز على body */
await page.click("#shReset");
const afterReset=await where();
ok(afterReset && afterReset.inSheet, "٢د «إعادة تعيين» لا تُسقط التركيز إلى body (وإلا تعطّل الحاصر)", afterReset);

await page.click("#shX");
await page.waitForFunction(()=>!document.querySelector("#sheet").classList.contains("open"));
const rowSym = await page.evaluate(()=>document.querySelector(".mcard[data-sym]").dataset.sym);
await page.click(`.mcard[data-sym="${rowSym}"]`); await page.waitForSelector("#drawer.open");
await page.click("#drX");
await page.waitForFunction(()=>!document.querySelector("#drawer").classList.contains("open"));
await page.waitForTimeout(300);

/* الحالة المعلنة بعد الإغلاق */
for(const [sel,lbl] of [["#sheet","الورقة"],["#drawer","الدرج"]]){
  const a=await attrs(sel);
  ok(a && a.inert && a.ariaHidden==="true", `٣ ${lbl} المغلق يعود خارج الشجرتين`, a);
}
/* قابلية التركيز المباشرة داخل حوارٍ مغلق — مع حارس اللاجدوى (مرشّحون موجودون فعلاً) */
for(const [sel,lbl] of [["#sheet","#sheet"],["#drawer","#drawer"]]){
  const r=await reachableInside(sel);
  ok(r.count>0, `٤ ${lbl} يحوي مرشّحين للتركيز (وإلا فالقياس زائف)`, r);
  ok(r.reachable.length===0, `٤ لا عنصر داخل ${lbl} المغلق يستقبل التركيز`, r.reachable);
}
/* الدرج يُسَد ولا يُفرَّغ: موقفٌ معلن — إن بدأ تفريغُه مستقبلاً يسقط هذا التأكيد */
const drKept=await page.evaluate(()=>({ len:document.querySelector("#drawer").innerHTML.length,
                                        inert:document.querySelector("#drawer").hasAttribute("inert") }));
ok(drKept.len>0 && drKept.inert, "٤ج الدرج المغلق يُسَد بـinert ولا يُفرَّغ (موقف معلن)", drKept);

/* أرضيةُ visibility — الإجراء الذي لا يتعلّق بأرضية inert ولا بنجاح JS */
const vis = sel => page.evaluate(x=>getComputedStyle(document.querySelector(x)).visibility, sel);
for(const [sel,lbl] of [["#sheet","الورقة"],["#drawer","الدرج"]])
  ok(await vis(sel)==="hidden", `٤د ${lbl} المغلق visibility:hidden (أرضيةٌ في كل متصفّح)`, await vis(sel));
await page.click("#fabFilters"); await page.waitForSelector("#sheet.open");
ok(await vis("#sheet")==="visible", "٤هـ الورقة المفتوحة visibility:visible");
/* الانزلاق محفوظ: التأخير يُبقيها مرئيةً طولَ الـ220ms ثم تُخفى.
   والإغلاق بقناته الحقيقية لا بنزع .open: نزعُه يتخطّى closeSheet فتبقى الخلفية
   inert — وهذا بعينه ما أفسد هذا القياس أولَ مرة. */
await page.click("#shX");
await page.waitForTimeout(60);
const midSlide = await vis("#sheet");
await page.waitForTimeout(340);
const afterSlide = await vis("#sheet");
ok(midSlide==="visible" && afterSlide==="hidden",
   "٤و الأرضية لا تكسر انزلاق الإغلاق (مرئيةٌ وسطه، مخفيةٌ بعده)", {midSlide, afterSlide});

/* الشقيق الرابع #tip: opacity:0 لا تُخرج من شجرة الإتاحة، فالنصّ المتقادم كان يُعلَن */
const tipState = await page.evaluate(()=>{
  const t=document.querySelector("#tip"), src=document.querySelector("[data-tip]");
  const out={ born:t.getAttribute("aria-hidden") };
  if(!src) return out;
  showTip(src); out.shown=t.getAttribute("aria-hidden");
  hideTip();    out.hidden=t.getAttribute("aria-hidden"); out.textKept=t.textContent.length>0;
  return out;
});
ok(tipState.born==="true", "٤ز ‏#tip يبدأ aria-hidden", tipState);
ok(tipState.shown===null, "٤ح الإظهار يرفع aria-hidden عن #tip", tipState);
ok(tipState.hidden==="true" && tipState.textKept,
   "٤ط الإخفاء يُعيده وإن بقي نصُّه (فلا نصَّ متقادماً يُعلَن)", tipState);

/* مسح Tab من رأس الصفحة إلى آخرها — الاتجاهان. والخلف أقوى: #sheet آخرُ أشقّائه */
for(const back of [false,true]){
  const sw=await tabSweep(back);
  const dir=back?"Shift+Tab":"Tab";
  ok(sw.candidates>10, `٥ مرشّحو المسح موجودون (${dir})`, sw.candidates);
  ok(sw.startedAt===sw.expectStart,
     `٥ مسح ${dir} بدأ من الطرف الموسوم فعلاً — لا من حيث تركه السابق`,
     {startedAt:sw.startedAt, expect:sw.expectStart});
  ok(sw.reachedEnd===true, `٥ مسح ${dir} بلغ الطرفَ الآخر فعلاً — لا تقصيرٌ صامت`, sw);
  ok(sw.hits.length===0, `٥ ${dir} لا يلمس أي عنصر داخل #sheet أو #drawer`, sw.hits.slice(0,4));
}

/* شاهدٌ سالب على الحرّاس المحلّية: نداءٌ مباشر يتخطّى inert وحجبَ النقر.
   واستثناءُ مُعالِجِ حدثٍ لا يبلغ موضعَ النداء — يُبلَّغ خطأً غير ملتقَط على window —
   فلا يُقاس بـtry حول .click() بل بعدّاد أخطاء الصفحة قبل الكتلة وبعدها. */
const errsBefore = errs.length;
const probes = await page.evaluate(async ()=>{
  const out={ ran:[] };
  const run=(k,f)=>{ try{ f(); out.ran.push(k); }catch(e){ out[k]="throw: "+e.message; } };
  run("shApply",  ()=>document.getElementById("shApply").click());
  run("optAdv",   ()=>document.querySelector('#sheet .opts[data-g="adv"] .opt').click());
  run("optScore", ()=>document.querySelector('#sheet .opts[data-g="score"] .opt').click());
  run("shSector", ()=>document.getElementById("shSector").dispatchEvent(new Event("change")));
  run("shReset",  ()=>document.getElementById("shReset").click());
  await new Promise(r=>setTimeout(r,80));
  out.draft = draft;
  out.stillClosed = !document.querySelector("#sheet").classList.contains("open");
  return out;
});
ok(probes.ran.length===5, "٦أ الشاهد السالب نفّذ المناداة الخمس فعلاً", probes.ran);
const newErrs = errs.slice(errsBefore);
ok(newErrs.length===0, "٦ب خمسُ مناداةٍ مباشرة على ورقةٍ مغلقة ⇒ صفر خطأ", newErrs.slice(0,4));
ok(probes.draft===null, "٦ج ولا يُحيي أيٌّ منها مسودّةً على ورقةٍ مغلقة", probes.draft);
ok(probes.stillClosed===true, "٦د ولا يُطبّق أيٌّ منها شيئاً (الورقة باقية مغلقة)", probes.stillClosed);

/* قنوات إغلاق الورقة الثلاث ⇒ التركيز يرجع إلى الزر الذي فتحها */
for(const [fn,label] of [
  [()=>page.click("#shX"), "✕"],
  [async()=>{ const h=await page.evaluate(()=>document.elementFromPoint(195,30).id);
              ok(h==="ovl","٧ نقطةُ نقر الطبقة تقع على #ovl فعلاً",h);
              await page.mouse.click(195,30); }, "الطبقة"],
  [()=>page.keyboard.press("Escape"), "Escape"],
]){
  await ensureClosed();
  await page.focus("#fabFilters"); await page.click("#fabFilters");
  await page.waitForSelector("#sheet.open");
  await fn();
  await page.waitForFunction(()=>!document.querySelector("#sheet").classList.contains("open"));
  const w=await where();
  ok(w && w.id==="fabFilters", `٧ إغلاق الورقة بـ${label} ⇒ التركيز يرجع إلى #fabFilters`, w);
}

/* الدرج: الإغلاق لا يسرق التركيز إلى sheetOpener (وقد صار مأهولاً بالدورة أعلاه).
   ولا قناةَ طبقةٍ للدرج على 390px: `.drawer{width:100%}` تحت 768px فيغطّي #ovl — تُقاس
   في سياق سطح المكتب أدناه بدل أن تُتخطّى صامتةً. */
for(const [fn,label] of [
  [()=>page.click("#drX"), "✕"],
  [()=>page.keyboard.press("Escape"), "Escape"],
  [()=>page.click("#drReturn"), "زر العودة"],
]){
  await ensureClosed();
  await page.focus(`.mcard[data-sym="${rowSym}"]`);
  await page.click(`.mcard[data-sym="${rowSym}"]`);
  await page.waitForSelector("#drawer.open");
  await fn();
  await page.waitForFunction(()=>!document.querySelector("#drawer").classList.contains("open"));
  const w=await where();
  ok(w && w.sym===rowSym, `٨ إغلاق الدرج بـ${label} ⇒ التركيز يرجع إلى الصف لا إلى sheetOpener`, w);
}
const ovlCovered=await page.evaluate(()=>{
  const d=document.querySelector("#drawer").getBoundingClientRect();
  return { w:Math.round(d.width), vw:window.innerWidth };
});
ok(ovlCovered.w===ovlCovered.vw, "٨د الدرج يغطّي العرض كلّه على 390px (فلا قناة طبقة له هنا)", ovlCovered);

/* التداخل ورقة/درج — مقيس لا مفترض */
await ensureClosed();
await page.click("#fabFilters"); await page.waitForSelector("#sheet.open");
const cardInert=await page.evaluate(s=>({ inert:!!document.querySelector(s).closest("[inert]"),
  drawerOpen:document.querySelector("#drawer").classList.contains("open") }), `.mcard[data-sym="${rowSym}"]`);
ok(cardInert.inert && !cardInert.drawerOpen, "٩أ الورقة مفتوحة ⇒ الصفوف inert فلا درج يُفتح فوقها", cardInert);
await ensureClosed();
await page.click(`.mcard[data-sym="${rowSym}"]`); await page.waitForSelector("#drawer.open");
const fabInert=await page.evaluate(()=>({ inert:!!document.querySelector("#fabFilters").closest("[inert]"),
  sheetOpen:document.querySelector("#sheet").classList.contains("open") }));
ok(fabInert.inert && !fabInert.sheetOpen, "٩ب الدرج مفتوح ⇒ #fabFilters inert فلا ورقة تُفتح فوقه", fabInert);

/* حرّاسُ انحدارٍ على ثلاثِ ثابتاتٍ كانت بلا حارس (ختم المراجعة الثاني) */
/* الثابتةُ تُستعلَم على **كل** سليل، لا على مخالفها الأوّل: استعلامُ
   `#chartTabs button` وحده كان يحرس ما عُولج ويعمى عن .dr-x و.cmd-btn و.sheet .opt —
   ومنها #drX و#shX نفساهما، فبقيت النافذةُ قائمةً وقد أُعلن إغلاقُها. */
const visTrans = await page.evaluate(()=>{
  const bad=[]; let n=0;
  for(const host of ["#sheet","#drawer"]) for(const el of document.querySelectorAll(host+" *")){
    n++;
    const cs=getComputedStyle(el);
    const props=cs.transitionProperty.split(",").map(x=>x.trim());
    const durs=cs.transitionDuration.split(",").map(x=>parseFloat(x)||0);
    const dels=cs.transitionDelay.split(",").map(x=>parseFloat(x)||0);
    let i=-1; props.forEach((pr,k)=>{ if(pr==="visibility"||pr==="all") i=k; });  /* الأخيرةُ تُرجَّح */
    if(i<0) continue;
    const d=durs[i%durs.length]||0, dl=dels[i%dels.length]||0;
    if(d>0||dl>0) bad.push({el:el.id||el.className||el.tagName, prop:props[i], dur:d, delay:dl});
  }
  return { n, bad };
});
ok(visTrans.n>20, "٩ز سلائلُ الحوارين موجودةٌ للاستعلام (وإلا فالقياس زائف)", visTrans.n);
ok(visTrans.bad.length===0,
   "٩ز لا سليلَ في الحوارين يُنقل visibility بمدّةٍ أو تأخير (فلا نافذةَ فوق الأرضية)",
   visTrans.bad.slice(0,6));

await ensureClosed();
await page.click(`.mcard[data-sym="${rowSym}"]`); await page.waitForSelector("#drawer.open");
await page.click("#drX");
await page.waitForFunction(()=>!document.querySelector("#drawer").classList.contains("open"));
ok(await page.evaluate(()=>lastFocus)===null,
   "٩ح ‏lastFocus يُصفَّر بعد الإغلاق (مرآةُ sheetOpener، لا تناظرٌ شكليّ)");

/* iOS: لمسةُ زرٍّ لا تُركّزه فالفاتحُ body — فلا يُختلق مكانٌ في كل إغلاق */
await ensureClosed();
await page.evaluate(()=>{ try{ document.activeElement.blur(); }catch(e){} openSheet(); });
await page.waitForSelector("#sheet.open");
ok(await page.evaluate(()=>sheetOpener===document.body), "٩ط الحالُ محاكًى: الفاتحُ body");
await page.click("#shX");
await page.waitForFunction(()=>!document.querySelector("#sheet").classList.contains("open"));
const noInvent=await where();
ok(noInvent && noInvent.body,
   "٩ي فاتحٌ body ⇒ لا مرتَدَّ يَنقل التركيز إلى رأس الصفحة", noInvent);

/* التداخل المُجبَر — شبكةُ الأمان تُقاس تامّةً لا نصفَ شبكة: lastFocus يصير داخل
   ورقةٍ سَتُسَد، فنداءُ تركيزه كان يفشل صامتاً فيهبط إلى body في الخطوة التالية. */
await ensureClosed();
/* والصفحةُ ممرَّرة: عند scrollY=0 يقع المرتَدُّ في المدى بلا علاجٍ، فالقياسُ عندها
   زائف — ومقيسُ الختم كان top=-970 على صفحةٍ ممرَّرة. */
await page.evaluate(()=>window.scrollTo(0,1200));
await page.waitForTimeout(60);
await page.click("#fabFilters"); await page.waitForSelector("#sheet.open");
await page.evaluate(s=>openDrawer(s), rowSym);
await page.waitForSelector("#drawer.open");
const both=await page.evaluate(()=>({ sh:document.querySelector("#sheet").classList.contains("open"),
                                      dr:document.querySelector("#drawer").classList.contains("open") }));
ok(both.sh && both.dr, "٩د الحالُ المُجبَر تحقّق فعلاً (وإلا فالقياس زائف)", both);
await page.click("#shX");
const step1=await where();
ok(step1 && step1.id==="drX", "٩هـ إغلاق الورقة فوق درجٍ مفتوح ⇒ التركيز إلى #drX", step1);
await page.keyboard.press("Escape");
await page.waitForFunction(()=>!document.querySelector("#drawer").classList.contains("open"));
const step2=await where();
ok(step2 && !step2.body, "٩و ثم إغلاق الدرج ⇒ التركيز لا يهبط إلى body", step2);
/* والمرتَدُّ يُقاس موضعُه على مسارٍ **قابلٍ للوصول** لا مُجبَر، و**بعد استقرار
   الإزاحة** لا قبلها: فكُّ قفلِ الجسم يُعيد الإزاحةَ المحفوظة بعد الارتداد، فقياسٌ
   قبله يُعلن سلامةً ثم يستقرّ العنصرُ خارج الشاشة (مقيسٌ عند الختم: top=-176).
   المسار: صفحةٌ ممرَّرة ⇒ لمسُ بطاقة ⇒ تغيُّرُ العرض والدرجُ مفتوح (تدويرُ جهاز)
   فيُفصَل lastFocus ⇒ Escape ⇒ المرتَدّ. */
await ensureClosed();
await page.waitForFunction(()=>document.documentElement.scrollHeight>8000);
/* ‏scroll-behavior:smooth يجعل scrollTo انتقالاً، فقياسٌ بعده بـ80ms يقع وسطه
   (مقيس: 54 ثم 166 ثم 196 على ثلاث مناداة) — فيُطلب الفوريُّ ويُنتظَر الاستقرار. */
await page.evaluate(()=>window.scrollTo({top:3000, behavior:"instant"}));
await page.waitForFunction(()=>{
  const y=window.scrollY;
  if(window.__lastY===y){ return true; }
  window.__lastY=y; return false;
}, null, { polling:120, timeout:5000 });
const scrolledTo = await page.evaluate(()=>Math.round(window.scrollY));
ok(scrolledTo>200, "٩ز٢أ الصفحةُ ممرَّرةٌ فعلاً قبل القياس (وإلا مرّ عند scrollY=0 زائفاً)", scrolledTo);
/* بطاقةٌ **مرئيةٌ الآن** لا الأولى: نقرُ Playwright يجرّ هدفَه إلى المدى، فاختيارُ
   الأولى يُعيد الإزاحة إلى الصفر قبل القفل فيَنقض الشرطَ الذي يقيسه هذا التأكيد. */
const farSym = await page.evaluate(()=>{
  const v=[...document.querySelectorAll(".mcard[data-sym]")]
    .find(c=>{ const r=c.getBoundingClientRect(); return r.top>0 && r.top<innerHeight; });
  return v ? v.dataset.sym : null;
});
ok(!!farSym, "٩ز٢ب بطاقةٌ مرئيةٌ على الإزاحة الحالية (وإلا فالقياس زائف)", farSym);
await page.click(`.mcard[data-sym="${farSym}"]`);
await page.waitForSelector("#drawer.open");
const lockedAt = await page.evaluate(()=>parseInt(document.body.style.top,10)||0);
ok(lockedAt<-200, "٩ز٢ج القفلُ حفظ إزاحةً غيرَ صفرية (شرطُ القياس)", lockedAt);
await page.setViewportSize({width:1280,height:900});
await page.waitForTimeout(120);
ok(await page.evaluate(s=>{ const el=document.querySelector(s);
     return !el || el.getClientRects().length===0; }, `.mcard[data-sym="${farSym}"]`),
   "٩ز٢د تغيُّرُ العرض فصل الهدفَ المحفوظ فعلاً (وإلا فلا مرتَدَّ يُقاس)");
const probe = () => page.evaluate(()=>{
  const a=document.activeElement; if(!a||a===document.body) return {body:true};
  const r=a.getBoundingClientRect();
  return { who:a.id||a.className||a.tagName, top:Math.round(r.top),
           scrollY:Math.round(window.scrollY),
           inView:r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth };
});
await page.keyboard.press("Escape");
await page.waitForFunction(()=>!document.querySelector("#drawer").classList.contains("open"));
const at0=await probe();
await page.waitForTimeout(700);
const at700=await probe();
/* ثابتتان، وكلتاهما مُبرهَنةٌ بطفرة (نزعُ ترجيح المدى من restoreFocus يُسقطهما):
   المرتَدُّ في المدى **لحظةَ الإغلاق وبعد الاستقرار** — لا لحظةً واحدةً وسط حركة —
   و**الإزاحةُ لا تنزلق** بعده: مقيسٌ أن الوقوعَ على عنصرٍ بعيدٍ يجرّ الصفحةَ كلَّها
   (2260 ⇒ 0) لأن focus() يُمرّر وscroll-behavior:smooth يُحوّله انزلاقاً. */
ok(at0.inView===true && at700.inView===true,
   "٩ز٢ المرتَدُّ في المدى المرئي لحظةَ الإغلاق وبعد الاستقرار", {at0, at700});
ok(at0.scrollY===at700.scrollY,
   "٩ز٢هـ والإزاحةُ لا تنزلق بعد الإغلاق (لا قفزةَ صفحةٍ تحت المستخدم)", {at0, at700});
await page.setViewportSize({width:390,height:844});
await page.waitForTimeout(120);
await ensureClosed();

/* Escape ولا حوار مفتوح — لا يسرق التركيز */
await ensureClosed();
await page.focus(`.mcard[data-sym="${rowSym}"]`);
await page.keyboard.press("Escape");
const afterEsc=await where();
ok(afterEsc && afterEsc.sym===rowSym, "٩ج ‏Escape ولا حوار مفتوح ⇒ التركيز حيث هو", afterEsc);

/* عدم انحدار وظيفي: الورقة ما زالت تُفلتر */
await ensureClosed();
const before=await page.evaluate(()=>document.querySelectorAll(".mcard[data-sym]").length);
await page.click("#fabFilters"); await page.waitForSelector("#sheet.open");
await page.click('#sheet .opts[data-g="score"] .opt[data-v="80"]');
await page.click("#shApply");
await page.waitForFunction(()=>!document.querySelector("#sheet").classList.contains("open"));
const after=await page.evaluate(()=>({ min:state.minScore, n:document.querySelectorAll(".mcard[data-sym]").length }));
ok(after.min===80, "١٠أ «تطبيق» ينقل الحدّ إلى state.minScore=80", after);
ok(after.n>0 && after.n<before, "١٠ب عدد البطاقات انخفض فعلاً (العلاج لم يُجمّد الورقة)", {before, ...after});

ok(errs.length===0, "١١ صفر خطأ JS على 390×844", errs.slice(0,6));
if(ext.length) console.log(`  ℹ️ ${ext.length} طلباً خارجياً محجوباً (لا يُفشل): ${[...new Set(ext)].join(", ")}`);
await ctx.close();
}

/* ════════════ ٢) سطح المكتب 1280×900 — قناة طبقة الدرج ════════════ */
console.log("── قناة طبقة الدرج على 1280×900 ──");
{
const { ctx, page, errs, ext, where, ensureClosed } = await openPage(1280,900);
const rowSym = await page.evaluate(()=>document.querySelector("tr[data-sym]").dataset.sym);
await ensureClosed();
await page.focus(`tr[data-sym="${rowSym}"]`);
await page.click(`tr[data-sym="${rowSym}"]`);
await page.waitForSelector("#drawer.open");
const hit=await page.evaluate(()=>document.elementFromPoint(window.innerWidth-40,40).id);
ok(hit==="ovl", "١٢أ الطبقة مكشوفةٌ خارج الدرج على 1280px", hit);
await page.mouse.click(1240,40);
await page.waitForFunction(()=>!document.querySelector("#drawer").classList.contains("open"));
const w=await where();
ok(w && w.sym===rowSym, "١٢ب إغلاق الدرج بالطبقة ⇒ التركيز يرجع إلى الصف", w);
ok(errs.length===0, "١٢ج صفر خطأ JS على 1280×900", errs.slice(0,6));
if(ext.length) console.log(`  ℹ️ ${ext.length} طلباً خارجياً محجوباً (لا يُفشل): ${[...new Set(ext)].join(", ")}`);
await ctx.close();
}

await browser.close(); server.close();
console.log(`${fail?"❌":"✅"} ${pass} نجحت، ${fail} فشلت  ·  ${PAGE}`);
process.exit(fail?1:0);
