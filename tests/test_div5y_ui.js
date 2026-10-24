// §8-ص: عمود «متوسط 5 سنوات» ووسومه في الواجهة — بلا jsdom، يستخرج من uat.html نفسه.
// الاستعمال: node tests/test_div5y_ui.js
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log("  ✅ " + m); } else { fail++; console.log("  ❌ " + m); } };

const uat = fs.readFileSync(ROOT + "/uat.html", "utf8");
const a = uat.indexOf("const d5Of"), b = uat.indexOf("function dyCell");
if (a < 0 || b < 0) throw new Error("مرساة d5 مفقودة في uat.html");
const stubs = `const priceOf=s=>(s.dailyExtra&&s.dailyExtra.lastClose)||s.currentPrice;
const esc=x=>String(x); const fmt=(v,d=2)=>Number(v).toFixed(d);
const impliedEpsAnnual=s=>s._eps??null;`;
const F = new Function(stubs + uat.slice(a, b) + "\nreturn {d5Of, d5Flags, d5Cell};")();

const b3060 = { window: [2021, 2025], perYear: { 2021: 2.25, 2022: 1.5, 2023: 1.5, 2024: 1.25, 2025: 1.25 },
                avg: 1.55, n: 5, nPaid: 5, flags: {} };
const s = { currentPrice: 13.54, dividend5y: b3060, financials: { netIncome: 104467957 }, _eps: 0.663 };
ok(Math.abs(F.d5Of(s) - 11.45) < 0.01, "3060: العائد الخمسي على 13.54 = 11.45%");
const f = F.d5Flags(s);
ok(f[0] === "المتوسط يفوق ربح السهم في آخر سنة" && f[1] === "متناقص سنة بعد سنة" && f.length === 2,
   "3060: وسما التغطية (1.55 > 0.66) والتناقص، بالأولوية");
ok(F.d5Cell(s).startsWith("11.45".slice(0, 4)) && F.d5Cell(s).includes("⚠️"), "الخلية: العائد مع ⚠️");
ok(F.d5Flags({ ...s, financials: { netIncome: -5 } })[0] === "الشركة خاسرة في آخر سنة", "خسارة ⇒ وسم الخسارة أولاً");
const ex = { ...s, _eps: 10, dividend5y: { ...b3060, perYear: { 2021: 1, 2022: 1, 2023: 3.5, 2024: 1, 2025: 1 }, avg: 1.5 } };
ok(F.d5Flags(ex).includes("يتضمن توزيعاً استثنائياً") && !F.d5Flags(ex).includes("متناقص سنة بعد سنة"),
   "سنة ≥ ضعف الوسيط ⇒ «استثنائي»، وغير الرتيب لا يوسم متناقصاً");
ok(F.d5Of({ currentPrice: 10, dividend5y: { ...b3060, avg: null, n: 1 } }) === null && F.d5Cell({ currentPrice: 10 }) === "—",
   "أقل من سنتين أو بلا كتلة ⇒ «—»");
const nn = { ...s, _eps: 10, dividend5y: { ...b3060, perYear: { 2021: 1, 2022: null, 2023: 1.2, 2024: 1.1, 2025: 1 }, n: 4 } };
ok(F.d5Flags(nn).length === 0, "السنة غير المحسومة (null) خارج سلسلة الوسوم");

// الجدول: العمود في COLS، وخلية في الصف، ومفتاح ترتيب، وعمود 12 شهراً باقٍ
ok(/\{key:"dy5",\s+label:"متوسط 5 سنوات", sortable:true/.test(uat) && /key:"dy",\s+label:"عائد التوزيعات"/.test(uat),
   "COLS: «متوسط 5 سنوات» مضاف و«عائد التوزيعات» (12 شهراً) باقٍ");
ok(uat.includes('<td class="num col-p2">${d5Cell(s)}</td>') && uat.includes("dy5:s=>d5Of(s)??-1"), "خلية الصف ومفتاح الترتيب");
ok(uat.includes('cell("متوسط التوزيع 5 سنوات"'), "خلية الدرج");
const tpl = fs.readFileSync(ROOT + "/template.html", "utf8");
ok(tpl.includes("const d5Of"), "template.html مولَّد من uat.html");

console.log("\n" + (fail ? "❌ " : "✅ ") + pass + " نجحت، " + fail + " فشلت");
process.exit(fail ? 1 : 0);
