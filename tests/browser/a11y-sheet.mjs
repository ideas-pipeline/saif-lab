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
  /* مسح Tab من رأس الصفحة حتى تمام الدورة. كشفُ التمام بهوية العنصر لا بتوقيعه:
     مئات البطاقات تتشابه صنفاً وتخلو من المعرّف، فالمقارنة النصّية تُعلن الدورة
     تامّةً بعد ثلاث خطوات (أوّلُ ما أعطى هذا الحزام نتيجةً زائفة). */
  async function tabSweep(back=false, cap=3000){
    await page.evaluate(()=>{ try{ document.activeElement&&document.activeElement.blur(); }catch{} window.__swFirst=null; });
    const hits=[]; let steps=0, seen=new Set();
    for(let i=0;i<cap;i++){
      await page.keyboard.press(back?"Shift+Tab":"Tab"); steps++;
      const st=await page.evaluate(()=>{
        const a=document.activeElement;
        if(!a||a===document.body) return { end:true };
        if(window.__swFirst===null) window.__swFirst=a;
        else if(window.__swFirst===a) return { end:true };
        return { end:false, id:a.id||null, cls:a.className||null, tag:a.tagName,
                 inSheet:!!a.closest("#sheet"), inDrawer:!!a.closest("#drawer") };
      });
      if(st.end) break;
      seen.add(`${st.tag}#${st.id}.${st.cls}`);
      if(st.inSheet||st.inDrawer) hits.push(st);
    }
    return { steps, hits, distinct:seen.size };
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

/* مسح Tab من رأس الصفحة إلى آخرها — الاتجاهان. والخلف أقوى: #sheet آخرُ أشقّائه */
for(const back of [false,true]){
  const sw=await tabSweep(back);
  const dir=back?"Shift+Tab":"Tab";
  ok(sw.distinct>=5, `٥ مسح ${dir} غطّى الصفحة فعلاً (لا تركيزٌ عالقٌ على body)`, sw);
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
