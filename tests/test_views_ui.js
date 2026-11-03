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
  "\nreturn {setData:v=>{DATA=v}, tasiChange, tasiCloseHtml, sessionDate, inSession, divEventsCount, VIEWS};")();
const V = id => F.VIEWS.find(v => v.id === id);

console.log("سطر تاسي");
const rg = { indexValue: 9876.13, prevClose: 9882.85, change: -6.72, changePct: -0.07, date: "2026-11-03" };
let h = F.tasiCloseHtml(rg);
ok(h.includes("تاسي أغلق") && h.includes('<b class="tv num">9,876.13</b>'), "الإغلاق بخط عريض بمنزلتين");
ok(h.includes("▼") && h.includes("chg-dn") && h.includes('<span class="num">6.72</span> نقطة') && h.includes("(−0.07%)"),
   "هبوط: ▼ و«6.72 نقطة» و«(−0.07%)» باللون الأحمر، والرقم معزول عن كلمة «نقطة»");
ok(h.includes("2026-11-03") && h.includes('class="sr-only">انخفض'), "تاريخ الجلسة، ونص لقارئ الشاشة");
h = F.tasiCloseHtml({ indexValue: 10000, prevClose: 9900, change: 100, changePct: 1.01 });
ok(h.includes("▲") && h.includes("chg-up") && h.includes("100</span> نقطة") && h.includes("(+1.01%)"), "صعود: ▲ و+");
ok(JSON.stringify(F.tasiChange({ indexValue: 9876.13, prevClose: 9882.85 })) === '{"pts":-6.72,"pct":-0.07}',
   "change غائب ⇒ من indexValue − prevClose (والنسبة كذلك)");
h = F.tasiCloseHtml({ indexValue: 9876.13, changePct: -0.07 });
ok(!h.includes("نقطة") && h.includes("(−0.07%)") && h.includes("▼"), "prevClose غائب ⇒ النسبة وحدها");
ok(F.tasiCloseHtml({}) === "تاسي <b>—</b>", "بلا مؤشر ⇒ «—»");
h = F.tasiCloseHtml({ indexValue: 9876.13, change: 0, changePct: 0 });
ok(h.includes("■") && h.includes("chg-flat") && h.includes("بلا تغير"), "بلا تغير ⇒ ■ رمادي");

console.log("التبويبات");
F.setData({ marketRegime: { date: "2026-11-03" }, upcomingDividends: [
  { eligDate: "2026-11-05" }, { distDate: "2026-11-03" }, { eligDate: "2026-10-01", distDate: "2026-10-20" }] });
const mk = (sym, chg, date = "2026-11-03", extra = {}) => ({ symbol: sym, dailyChange: chg, dailyExtra: { lastDate: date }, ...extra });
const S = [mk("A", 6.3), mk("B", 1.2), mk("C", -9.11), mk("D", -0.5), mk("E", 0), mk("F", null),
           mk("G", 4.0, "2026-10-30"), mk("H", -3.0, "2026-10-30"), { symbol: "I", dailyChange: 2 }];
const ids = F.VIEWS.map(v => v.id);
ok(ids.slice(0, 4).join() === "market,gainers,losers,yield" && ids.includes("dividends") && ids.includes("mine"),
   "الترتيب: السوق ثم ارتفاعاً ثم انخفاضاً ثم عائداً، والبقية باقية");
ok(S.filter(V("gainers").fn).map(s => s.symbol).join() === "A,B",
   "ارتفاعاً: الموجب فقط من آخر جلسة — لا صفر ولا null ولا جلسة قديمة (G) ولا بلا تاريخ (I)");
ok(S.filter(V("losers").fn).map(s => s.symbol).join() === "C,D", "انخفاضاً: السالب من آخر جلسة فقط (H قديمة خارج)");
ok(JSON.stringify(V("gainers").sort) === '{"key":"chg","dir":-1}' && JSON.stringify(V("losers").sort) === '{"key":"chg","dir":1}',
   "الفرز: ارتفاعاً تنازلي، انخفاضاً تصاعدي (الأشد هبوطاً أولاً)");
F.setData({});
ok(F.inSession(mk("X", 1, "2020-01-01")), "بلا تاريخ جلسة في البيانات ⇒ لا يُستبعد أحد");
ok(V("yield").fn({ _dy: 3.2 }) && !V("yield").fn({ _dy: 0 }) && !V("yield").fn({}) &&
   JSON.stringify(V("yield").sort) === '{"key":"dy","dir":-1}', "الأعلى عائداً: dy>0 مرتب تنازلياً");
F.setData({ upcomingDividends: [{ eligDate: "2026-11-05" }, { distDate: "2026-11-03" }, { eligDate: "2026-10-01", distDate: "2026-10-20" }] });
ok(V("dividends").calendarOnly === true && V("dividends").count() === 2 && V("dividends").label === "مفكرة التوزيعات"
   && S.filter(V("dividends").fn).length === 0, "مفكرة التوزيعات: بلا جدول، وعدّادها الأحداث القادمة (2) لا الشركات");

console.log("ربط العرض");
const rb = uat.slice(uat.indexOf("function renderBody(){"), uat.indexOf("function renderBody(){") + 6000);
ok(/if\(view\.calendarOnly\)\{[\s\S]{0,300}\$\("body"\)\.innerHTML=divCalendarHtml\(\);\s*return;/.test(rb),
   "renderBody: المفكرة وحدها ثم return — لا جدول ولا بطاقات");
ok(rb.includes('state.view==="yield"?dyNoteHtml()') && rb.includes('state.view==="yield"&&dyOf(s)!=null'),
   "ملاحظة العائد وشارة العائد في البطاقة ⇒ «الأعلى عائداً»");
ok(uat.includes('state.dyRatedOnly && state.view==="yield"') && uat.includes('const view=VIEWS.find(v=>v.id==="yield");'),
   "«المقيَّمة فقط» وعدّاد الأعلى عشرة ⇒ «الأعلى عائداً»");
ok(!/state\.view==="dividends"/.test(uat), "لا أثر باقٍ لجدول التوزيعات القديم");
ok(rb.includes("view.session?") && rb.includes("لا يدخل تقييم سيف"), "ملاحظة الجلسة فوق ارتفاعاً/انخفاضاً");
ok(uat.includes('<div class="regime-line">${tasiCloseHtml(rg)}'), "سطر المؤشر يستعمل tasiCloseHtml");
ok(uat.includes('data-goto="dividends"'), "بلاطة «مفكرة التوزيعات» تفتح التبويب نفسه");

const tpl = fs.readFileSync(ROOT + "/template.html", "utf8");
ok(tpl.includes("function tasiCloseHtml") && tpl.includes('{id:"gainers"'), "template.html مولَّد من uat.html");

console.log("\n" + (fail ? "❌ " : "✅ ") + pass + " نجحت، " + fail + " فشلت");
process.exit(fail ? 1 : 0);
