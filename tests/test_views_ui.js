// §8-و: سطر تاسي وتبويبات «الأعلى ارتفاعاً/الأكثر انخفاضاً/الأعلى عائداً» و«مفكرة التوزيعات» وحدها.
// بلا jsdom — يستخرج الكتلة من uat.html نفسه. الاستخدام: node tests/test_views_ui.js
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log("  ✅ " + m); } else { fail++; console.log("  ❌ " + m); } };

const uat = fs.readFileSync(ROOT + "/uat.html", "utf8");
const a = uat.indexOf("/* ─── §8-و سطر تاسي"), b = uat.indexOf("function renderViews(){");
if (a < 0 || b < 0 || b < a) throw new Error("مرساة §8-و مفقودة في uat.html");
const pick = re => { const m = uat.match(re); if (!m) throw new Error("تعريف مفقود: " + re); return m[0]; };
const pre = [/^const esc=.*$/m, /^const fmt=.*$/m, /^const chgOf=.*$/m].map(pick).join("\n") + `
let DATA={}; const todayStr=()=>"2026-11-03";
const dyOf=s=>s._dy??null, rated=s=>!!s._rated, isc=s=>s._isc||{}, timingState=s=>s._t||"";`;
const F = new Function(pre + uat.slice(a, b) +
  "\nreturn {setData:v=>{DATA=v}, tasiChange, tasiCloseHtml, sessionDate, inSession, divEventsCount, evPhrase, VIEWS};")();
const V = id => F.VIEWS.find(v => v.id === id);

console.log("سطر تاسي");
const rg = { indexValue: 9876.13, prevClose: 9882.85, change: -6.72, changePct: -0.07, date: "2026-11-03" };
let h = F.tasiCloseHtml(rg);
ok(h.includes("تاسي أغلق") && h.includes('<b class="tv num">9,876.13</b>'), "الإغلاق بخط عريض بمنزلتين");
ok(h.includes("▼") && h.includes("chg-dn") && h.includes('<span class="num">6.72</span> نقطة') && h.includes("(-0.07%)"),
   "هبوط: ▼ و«6.72 نقطة» و«(-0.07%)» باللون الأحمر، والرقم معزول عن كلمة «نقطة»");
ok(h.includes("2026-11-03") && h.includes('class="sr-only">انخفض'), "تاريخ الجلسة، ونص لقارئ الشاشة");
ok(h.indexOf('class="sr-only">انخفض') < h.indexOf("6.72") && h.indexOf('aria-hidden="true">▼') < h.indexOf("sr-only"),
   "مراجعة UX: قارئ الشاشة يسمع «انخفض 6.72 نقطة» قبل الأرقام لا بعدها");
ok(!F.tasiCloseHtml({ indexValue: 9876.13 }).includes("sr-only"), "بلا تغيّر معروف ⇒ لا يُعلَن «بلا تغير» زوراً");
h = F.tasiCloseHtml({ indexValue: 10000, prevClose: 9900, change: 100, changePct: 1.01 });
ok(h.includes("▲") && h.includes("chg-up") && h.includes("100.00</span> نقطة") && h.includes("(+1.01%)"), "صعود: ▲ و+ ومنزلتان ثابتتان");
h = F.tasiCloseHtml({ indexValue: 9876.1, change: -0.4, changePct: 0 });
ok(h.includes("9,876.10") && h.includes("(-0.00%)") && h.includes("▼"),
   "منزلتان ثابتتان (9,876.10)، وإشارة النسبة من الاتجاه فلا «▼ … (0%)» (ملاحظة الناقد)");
ok(JSON.stringify(F.tasiChange({ indexValue: 9876.13, prevClose: 9882.85 })) === '{"pts":-6.72,"pct":-0.07}',
   "change غائب ⇒ من indexValue − prevClose (والنسبة كذلك)");
h = F.tasiCloseHtml({ indexValue: 9876.13, changePct: -0.07 });
ok(!h.includes("نقطة") && h.includes("(-0.07%)") && h.includes("▼"), "prevClose غائب ⇒ النسبة وحدها");
ok(F.tasiCloseHtml({}) === "تاسي <b>—</b>", "بلا مؤشر ⇒ «—»");
h = F.tasiCloseHtml({ indexValue: 9876.13, change: 0, changePct: 0 });
ok(h.includes("■") && h.includes("chg-flat") && h.includes("بلا تغير"), "بلا تغير ⇒ ■ رمادي");

console.log("التبويبات");
F.setData({ marketRegime: { date: "2026-11-03" }, upcomingDividends: [
  { eligDate: "2026-11-05" }, { distDate: "2026-11-03" }, { eligDate: "2026-10-01", distDate: "2026-10-20" }] });
const mk = (sym, chg, date = "2026-11-03", extra = {}) =>
  ({ symbol: sym, dailyChange: chg, dailyExtra: { lastDate: date }, priceUpdatedAt: date + " 16:20", ...extra });
const S = [mk("A", 6.3), mk("B", 1.2), mk("C", -9.11), mk("D", -0.5), mk("E", 0), mk("F", null),
           mk("G", 4.0, "2026-10-30"), mk("H", -3.0, "2026-10-30"), { symbol: "I", dailyChange: 2 },
           // 8190 الحقيقي (ختم الناقد): الشموع اليوم والسعر وتغيّره من 2026-09-10
           mk("J", 0.9, "2026-11-03", { priceUpdatedAt: "2026-09-10 16:20" }),
           mk("K", -2.0, "2026-11-03", { priceUpdatedAt: "2026-09-10 16:20" }),
           // تشغيلة بعد منتصف الليل: السعر مختوم باليوم التالي لجلسته — مقبول
           mk("L", 3.0, "2026-11-03", { priceUpdatedAt: "2026-11-04 00:30" })];
const ids = F.VIEWS.map(v => v.id);
ok(ids.join() === "market,gainers,losers,top,entry,reversal,yield,dividends,mine",
   "الترتيب (مراجعة UX): السوق ثم حركة الجلسة، ثم عروض سيف، ثم «الأعلى عائداً» ملاصقاً للمفكرة، ثم قائمتي");
ok(S.filter(V("gainers").fn).map(s => s.symbol).join() === "A,B,L",
   "ارتفاعاً: الموجب من آخر جلسة — لا صفر ولا null ولا شموع قديمة (G) ولا بلا تاريخ (I) ولا سعر قديم (J=8190)، وتشغيلة منتصف الليل (L) مقبولة");
ok(S.filter(V("losers").fn).map(s => s.symbol).join() === "C,D", "انخفاضاً: السالب من آخر جلسة فقط (H شموع قديمة وK سعر قديم خارج)");
ok(JSON.stringify(V("gainers").sort) === '{"key":"chg","dir":-1}' && JSON.stringify(V("losers").sort) === '{"key":"chg","dir":1}',
   "الفرز: ارتفاعاً تنازلي، انخفاضاً تصاعدي (الأشد هبوطاً أولاً)");
F.setData({});
ok(F.inSession(mk("X", 1, "2020-01-01")), "بلا تاريخ جلسة في البيانات ⇒ لا يُستبعد أحد");
ok(V("yield").fn({ _dy: 3.2 }) && !V("yield").fn({ _dy: 0 }) && !V("yield").fn({}) &&
   JSON.stringify(V("yield").sort) === '{"key":"dy","dir":-1}', "الأعلى عائداً: dy>0 مرتب تنازلياً");
F.setData({ upcomingDividends: [{ sym: "1", value: 1, eligDate: "2026-11-05" }, { sym: "2", value: 0.5, distDate: "2026-11-03" },
  { sym: "3", value: 1, eligDate: "2026-10-01", distDate: "2026-10-20" },
  { sym: "", value: 1, eligDate: "2026-11-09" }, { sym: "5", value: 0, eligDate: "2026-11-09" }] });
ok(V("dividends").calendarOnly === true && V("dividends").count() === 2 && V("dividends").label === "مفكرة التوزيعات"
   && S.filter(V("dividends").fn).length === 0, "مفكرة التوزيعات: بلا جدول، وعدّادها الأحداث القادمة (2) لا الشركات — وبشرط صفوف المفكرة نفسه (بلا رمز أو بقيمة صفرية يُسقط)");

console.log("ربط العرض");
const rb = uat.slice(uat.indexOf("function renderBody(){"), uat.indexOf("function renderBody(){") + 6000);
ok(/if\(view\.calendarOnly\)\{[\s\S]{0,500}\$\("body"\)\.innerHTML=divCalendarHtml\(\);\s*bindSymRows\(\);[^\n]*\n\s*return;/.test(rb),
   "renderBody: المفكرة وحدها ثم ربط صفوفها بالدرج ثم return (ختم الناقد: كانت لا تفتح الدرج)");
ok((rb.match(/bindSymRows\(\);/g) || []).length === 2 && uat.includes("function bindSymRows(){")
   && /function bindSymRows\(\)\{[\s\S]{0,300}openDrawer\(el\.dataset\.sym\)[\s\S]{0,120}key==="Enter"/.test(uat),
   "الربط (نقر وEnter) في دالة واحدة تُنادى في فرعي الجدول والمفكرة");
ok(uat.includes('${rows.length} ${evPhrase(rows.length)}') && !uat.includes("${rows.length} حدثاً"),
   "رأس المفكرة بتمييز العدد نفسه (لا «10 حدثاً»)");
ok(/else if\(prevV&&prevV\.session\) state\.sort=\{key:"score",dir:-1\};/.test(uat),
   "الخروج من عرض جلسة إلى عرض بلا فرز يعيد فرز الدرجة (لا يصعد الفارغ −999 بالتصاعدي)");
ok(rb.includes('state.view==="yield"?dyNoteHtml()') && rb.includes('state.view==="yield"&&dyOf(s)!=null'),
   "ملاحظة العائد وشارة العائد في البطاقة ⇒ «الأعلى عائداً»");
ok(uat.includes('state.dyRatedOnly && state.view==="yield"') && uat.includes('const view=VIEWS.find(v=>v.id==="yield");'),
   "«المقيَّمة فقط» وعدّاد الأعلى عشرة ⇒ «الأعلى عائداً»");
ok(!/state\.view==="dividends"/.test(uat), "لا أثر باقٍ لجدول التوزيعات القديم");
ok(rb.includes("view.session?") && rb.includes("لا يدخل تقييم سيف"), "ملاحظة الجلسة فوق ارتفاعاً/انخفاضاً");
ok(uat.includes('$("regime").innerHTML=`${tasiCloseHtml(rg)}') && uat.includes('<div class="regime-line" id="regime" role="region" aria-label="مؤشر السوق"></div>')
   && !/\$\("pulse"\)\.innerHTML=`[\s\S]{0,2500}regime-line/.test(uat.slice(uat.indexOf("function renderPulse(){"), uat.indexOf("function tasiChange("))),
   "سطر المؤشر يستعمل tasiCloseHtml، وهو شقيق للنبض لا داخله (على الجوال كان آخر الشريط الأفقي خارج الشاشة)");
ok(/@media\(max-width:767px\)\{[\s\S]{0,1200}\.regime-line\{font-size:11px; padding:4px 14px 6px\}/.test(uat)
   && !/\.regime-line\{[^}]*nowrap/.test(uat), "الجوال: السطر يلتف ولا يُمرَّر أفقياً — الإغلاق مرئي بلا تمرير");
ok(["0 أحداث قادمة","1 حدث قادم","2 حدثان قادمان","3 أحداث قادمة","10 أحداث قادمة","11 حدثاً قادماً","99 حدثاً قادماً","100 حدث قادم"]
   .every(t => { const n = +t.split(" ")[0]; return n + " " + F.evPhrase(n) === t; }), "تمييز العدد: «10 أحداث» لا «10 حدثاً»");
ok(rb.includes("setCmdOff(!!view.calendarOnly);") && rb.includes("${evPhrase(ne)}") && uat.includes("function setCmdOff(off){")
   && uat.includes("body.cal-view .fchips,body.cal-view .adv,body.cal-view .fab{display:none}"),
   "المفكرة: أدوات البحث والفلاتر معتَّمة معطَّلة، والشرائح واللوحة وزر الجوال مخفية");
ok(V("gainers").empty && V("losers").empty && rb.includes("لا تتوفر تغيّرات الأسهم لآخر جلسة") && rb.includes("et=view.empty+at"),
   "الحالة الصفرية لعرضي الجلسة: «لم يرتفع أي سهم» تُميَّز عن «لا تتوفر تغيّرات» (بيانات غائبة)");
ok(uat.includes('Math.abs(v.scrollLeft)>4') && uat.includes('$("views").addEventListener("scroll",updateViewsScrollHint'),
   "تلاشي التبويبات يتبع موضع التمرير فيزول عند آخر تبويب");
ok(uat.includes('data-goto="dividends"'), "بلاطة «مفكرة التوزيعات» تفتح التبويب نفسه");

const tpl = fs.readFileSync(ROOT + "/template.html", "utf8");
ok(tpl.includes("function tasiCloseHtml") && tpl.includes('{id:"gainers"'), "template.html مولَّد من uat.html");

console.log("\n" + (fail ? "❌ " : "✅ ") + pass + " نجحت، " + fail + " فشلت");
process.exit(fail ? 1 : 0);
