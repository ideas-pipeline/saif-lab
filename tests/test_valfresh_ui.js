// §8-ح: نضارة المؤشرات المالية من ختم الجلب اليومي (valuationInputs.updatedAt) لا من الحقول الأحفورية.
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
  "\nreturn {setData:v=>{DATA=v}, valUpdOf, valStale, frz, frzMark};")();

F.setData({ marketRegime: { date: "2026-11-05" } });
const fossil = { valuationUpdatedAt: "2026-08-04 16:23", valuationParts: { pe: "frozen", pb: "frozen", dividendYield: "frozen" } };
const live = { ...fossil, valuationInputs: { updatedAt: "2026-11-05" } };
ok(F.valUpdOf(live) === "2026-11-05", "التاريخ من valuationInputs.updatedAt لا من valuationUpdatedAt الأحفوري (3005)");
ok(!F.frz(live, "pe") && !F.frz(live, "pb") && !F.frz(live, "dividendYield") && F.frzMark(live, "pe") === "",
   "جلب اليوم ⇒ لا ❄️ ولو قال valuationParts «frozen»");
ok(!F.frz({ valuationInputs: { updatedAt: "2026-10-29" } }, "pe"), "جلب قبل 7 أيام (عطلة/أسبوعي) ⇒ ليس متقادماً");
const old = { valuationInputs: { updatedAt: "2026-08-04" } };
ok(F.frz(old, "pe") && F.frzMark(old, "pe").includes("غير محدّث منذ 2026-08-04"), "جلب من 08-04 ⇒ ❄️ مع تاريخ آخر جلب");
ok(F.frz({}, "pb") && F.frzMark({}, "pb").includes("لم يصل جلب جديد"), "بلا ختم جلب ⇒ متقادم");
F.setData({});
ok(!F.frz({ valuationInputs: { updatedAt: "2020-01-01" } }, "pe"), "بلا تاريخ مرجعي في البيانات ⇒ لا حكم بالتقادم");
F.setData({ lastUpdated: "2026-11-05 16:39 الرياض" });
ok(F.frz(old, "pe") && !F.frz(live, "pe"), "احتياط المرجع: lastUpdated حين يغيب marketRegime");

ok(!/valuationParts|valuationUpdatedAt\|\|/.test(uat.replace(/\/\*[\s\S]*?\*\//g, "")), "لا قراءة باقية للحقلين الأحفوريين خارج التعليقات");
ok(uat.includes("تحديث المؤشرات المالية: <span class=\"num\">${esc(valUpdOf(s))}</span>") && !uat.includes("المكوّنات الحية"),
   "تسمية الدرج «تحديث المؤشرات المالية»");
const tpl = fs.readFileSync(ROOT + "/template.html", "utf8");
ok(tpl.includes("function valStale(s){"), "template.html مولَّد من uat.html");

console.log("\n" + (fail ? "❌ " : "✅ ") + pass + " نجحت، " + fail + " فشلت");
process.exit(fail ? 1 : 0);
