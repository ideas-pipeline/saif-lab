// §8-ح: نضارة المؤشرات المالية بختم كل مكوّن من الجلب الأسبوعي (companyAsOf/divsAsOf)،
// لا من الحقول الأحفورية ولا من updatedAt (يُختم باليوم ولو فشل /company و/dividends).
// بلا jsdom — يستخرج الكتلة من uat.html نفسه. الاستخدام: node tests/test_valfresh_ui.js
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log("  ✅ " + m); } else { fail++; console.log("  ❌ " + m); } };

const uat = fs.readFileSync(ROOT + "/uat.html", "utf8");
const a = uat.indexOf("const VAL_STALE_NOTE="), b = uat.indexOf("function finCells(s){");
if (a < 0 || b < 0 || b < a) throw new Error("مرساة §8-ح مفقودة في uat.html");
const pick = re => { const m = uat.match(re); if (!m) throw new Error("تعريف مفقود: " + re); return m[0]; };
const F = new Function(pick(/^const esc=.*$/m) + "\nlet DATA={};\n" + uat.slice(a, b) +
  "\nreturn {setData:v=>{DATA=v}, valUpdOf, valStale, frz, frzMark, VAL_STALE_DAYS};")();

F.setData({ marketRegime: { date: "2026-11-05" } });
const fossil = { valuationUpdatedAt: "2026-08-04 16:23", valuationParts: { pe: "frozen", pb: "frozen", dividendYield: "frozen" } };
const live = { ...fossil, valuationInputs: { updatedAt: "2026-11-05", companyAsOf: "2026-11-05", divsAsOf: "2026-11-05",
                                             epsBasis: "provider", bookValueBasis: "provider" } };
ok(F.valUpdOf(live, "pe") === "2026-11-05" && F.valUpdOf(live, "dividendYield") === "2026-11-05",
   "الختم لكل مكوّن من companyAsOf/divsAsOf لا من valuationUpdatedAt الأحفوري (3005)");
ok(!F.frz(live, "pe") && !F.frz(live, "pb") && !F.frz(live, "dividendYield") && F.frzMark(live, "pe") === "",
   "جلب هذا الخميس ⇒ لا ❄️ ولو قال valuationParts «frozen»");

// المانع 1 (ختم الناقد): نجح /ratios وفشل /company ⇒ updatedAt اليوم وcompanyAsOf قديم
const partial = { valuationInputs: { updatedAt: "2026-11-05", companyAsOf: "2026-10-20", divsAsOf: "2026-11-05", epsBasis: "provider" } };
ok(F.frz(partial, "pe") && F.frz(partial, "pb") && !F.frz(partial, "dividendYield"),
   "فشل /company وحده ⇒ ❄️ على P/E وP/B لا على العائد (updatedAt اليوم لا يُخفي القديم)");
ok(F.frzMark(partial, "pe").includes("غير محدّث منذ 2026-10-20"), "التلميح يذكر ختم /company الفعلي");
const divOld = { valuationInputs: { companyAsOf: "2026-11-05", divsAsOf: "2026-10-01" } };
ok(!F.frz(divOld, "pe") && F.frz(divOld, "dividendYield"), "فشل /dividends وحده ⇒ ❄️ على العائد وحده");
ok(F.frz({ valuationInputs: { updatedAt: "2026-11-05" } }, "pe"), "updatedAt وحده بلا companyAsOf ⇒ غير محدّث (لا احتياط إليه)");
const fyd = { financialsUpdated: "2026-10-01", valuationInputs: { companyAsOf: "2026-11-05", epsBasis: "fy-derived", bookValueBasis: "provider" } };
ok(F.valUpdOf(fyd, "pe") === "2026-10-01" && F.frz(fyd, "pe") && !F.frz(fyd, "pb"),
   "EPS مشتق من /financials ⇒ أقدم الختمين لـP/E، وP/B على أساسه");

// المانع 2: الجلب أسبوعي — العتبة 10 أيام (7 + هامش 3)
ok(F.VAL_STALE_DAYS === 10, "العتبة 10 أيام");
F.setData({ marketRegime: { date: "2026-11-11" } });
ok(!F.frz(live, "pe"), "الأربعاء التالي (6 أيام) ⇒ ليس متقادماً");
F.setData({ marketRegime: { date: "2026-11-15" } });
ok(!F.frz(live, "pe"), "الأحد بعد خميس فائت (10 أيام) ⇒ ليس بعد");
F.setData({ marketRegime: { date: "2026-11-16" } });
ok(F.frz(live, "pe"), "الإثنين بعد خميس فائت (11 يوماً) ⇒ ❄️");
F.setData({ marketRegime: { date: "2026-11-05" } });
const old = { valuationInputs: { companyAsOf: "2026-08-04", divsAsOf: "2026-08-04" } };
ok(F.frz(old, "pe") && F.frzMark(old, "pe").includes("غير محدّث منذ 2026-08-04"), "جلب من 08-04 ⇒ ❄️ مع تاريخه");
ok(F.frz({}, "pb") && F.frzMark({}, "pb").includes("لم يصل جلب جديد"), "بلا valuationInputs (4035/5113) ⇒ متقادم");
ok(F.frz({ valuationInputs: { companyAsOf: "11/05/2026" } }, "pe") && F.frz({ valuationInputs: { companyAsOf: "2026-13-45" } }, "pe"),
   "تاريخ بغير صيغة الكاتب أو تالف ⇒ غير محدّث لا صمت");
F.setData({});
ok(!F.frz({ valuationInputs: { companyAsOf: "2020-01-01" } }, "pe"), "بلا تاريخ مرجعي ⇒ لا حكم بالتقادم");
F.setData({ lastUpdated: "2026-11-05 16:39 الرياض" });
ok(F.frz(old, "pe") && !F.frz(live, "pe"), "احتياط المرجع: lastUpdated حين يغيب marketRegime");

// المانع 3: العائد يُطوى على الرأس كـP/E وP/B
const rb = uat.slice(uat.indexOf("function renderBody(){"), uat.indexOf("function renderBody(){") + 9000);
ok(rb.includes('const dyFrozen=!!frzCol("dividendYield");')
   && rb.includes('c.key==="dy"?dyFrozen')
   && rb.includes("${dyCell(s,dyFrozen)}</td>") && rb.includes("عائد ${dyCell(s,dyFrozen)}"),
   "التقادم الشامل للعائد ⇒ ❄️ على الرأس، والصف والبطاقة يكتمانها");
ok(uat.includes('${colFrozen?"":frzMark(s,"dividendYield")}'), "dyCell يكتم ❄️ الصف حين يُطوى العمود");

ok(!/valuationParts|valuationUpdatedAt\|\|/.test(uat.replace(/\/\*[\s\S]*?\*\//g, "")), "لا قراءة باقية للحقلين الأحفوريين خارج التعليقات");
ok(uat.includes("آخر جلب للأساسيات (أسبوعي):") && !uat.includes("المكوّنات الحية") && !uat.includes("تحديث المؤشرات المالية"),
   "تسمية الدرج «آخر جلب للأساسيات (أسبوعي)» — تاريخ الجلب لا «تحديث» القسم كله");
const tpl = fs.readFileSync(ROOT + "/template.html", "utf8");
ok(tpl.includes("function valStale(s,k){"), "template.html مولَّد من uat.html");

console.log("\n" + (fail ? "❌ " : "✅ ") + pass + " نجحت، " + fail + " فشلت");
process.exit(fail ? 1 : 0);
