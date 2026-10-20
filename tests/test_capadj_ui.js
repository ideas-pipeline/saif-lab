// §8-ق: سلوك الواجهة بعد تعديل المنح — بلا jsdom. يستخرج من المصدر المنشور نفسه:
//   صفحة الدقة (calcReturn … rows): entryPriceAdj يحسب العائد، وdataFault يُخرج من الحكم
//   uat.html: impliedEpsAnnual وimpliedEpsAlt يقسمان العددين على sharesCapFactor
//   template-classic.html: isV3sc يقبل v3.1 للمستبعد (لا quality له)
// الاستعمال: node tests/test_capadj_ui.js
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log("  ✅ " + m); } else { fail++; console.log("  ❌ " + m); } };

// ── صفحة الدقة ──
const acc = fs.readFileSync(ROOT + "/watchlist-accuracy.html", "utf8");
const a = acc.indexOf("function calcReturn"), b = acc.indexOf("const autoRows");
if (a < 0 || b < 0) throw new Error("مرساة مفقودة في watchlist-accuracy.html");
const rowsOf = new Function("WATCHLIST", acc.slice(a, b) + "\nreturn {rows, statusBadge};");
const base = { symbol: "1030", type: "buy", category: "buy", track: "auto", entryDate: "2026-01-01",
               divsSince: 0, tasiRet: 0, periodDays: 200, currentPrice: 12.0 };
const { rows, statusBadge } = rowsOf([
  { ...base, entryPrice: 14.4, entryPriceAdj: 12.0 },
  { ...base, entryPrice: 14.4 },
  { ...base, symbol: "2200", entryPrice: 6.6, status: "closed", closePrice: 5.32, closeReason: "score_below_50",
    dataFault: { kind: "capaction-unadjusted", date: "2026-08-24", label: "أُغلق بعطب بيانات" } },
]);
ok(Math.abs(rows[0].ret) < 1e-9, "entryPriceAdj يحسب العائد (12 ÷ 12 = 0%)");
ok(Math.abs(rows[1].ret - (12 / 14.4 - 1) * 100) < 1e-9, "وبلاه على الخام (−16.7%)");
ok(rows[2].success === null && rows[2].dataFault === true, "dataFault ⇒ خارج الحكم (success = null)");
ok(statusBadge(rows[2].success, rows[2]).includes("عطب بيانات"), "وشارته «أُغلق بعطب بيانات»");

// ── uat.html: impliedEpsAnnual / impliedEpsAlt ──
const uat = fs.readFileSync(ROOT + "/uat.html", "utf8");
const u0 = uat.indexOf("function sharesCapK"), u1 = uat.indexOf("/* هامش ميت 5%");
if (u0 < 0 || u1 < 0) throw new Error("مرساة مفقودة في uat.html");
const E = new Function(uat.slice(u0, u1) + "\nreturn {impliedEpsAnnual, impliedEpsAlt};")();
const s = { financials: { netIncome: 3e9 },
            valuationInputs: { sharesOutstanding: 1.25e9, marketCap: 1.25e9 * 14.5, theirPrice: 14.5, sharesCapFactor: 0.833333 } };
ok(Math.abs(E.impliedEpsAnnual(s) - 2.0) < 1e-4, "impliedEpsAnnual على العدد الحالي (3 مليار ÷ 1.5 مليار)");
ok(Math.abs(E.impliedEpsAlt(s) - 2.0) < 1e-4, "impliedEpsAlt كذلك (القيمة السوقية المجمّدة ÷ k)");
const s0 = JSON.parse(JSON.stringify(s)); delete s0.valuationInputs.sharesCapFactor;
ok(Math.abs(E.impliedEpsAnnual(s0) - 2.4) < 1e-4 && Math.abs(E.impliedEpsAlt(s0) - 2.4) < 1e-4,
   "وبلا sharesCapFactor على المجمّد (2.4)");

// ── template-classic.html: isV3sc ──
const cl = fs.readFileSync(ROOT + "/template-classic.html", "utf8");
const line = cl.match(/^const isV3sc = .*$/m);
if (!line) throw new Error("isV3sc مفقود");
const isV3sc = new Function(line[0] + "\nreturn isV3sc;")();
ok(isV3sc({ criteriaVersion: "v3.1", filtered: true }), "isV3sc: مستبعد v3.1 بلا quality ⇒ v3");
ok(isV3sc({ criteriaVersion: "v3" }), "وv3 كما كان");
ok(!isV3sc({ criteriaVersion: "v30" }) && !isV3sc({ criteriaVersion: "v2.1" }), "ولا يقبل v30 ولا v2.1");

// ── uat.html: capNote — نص وصلة المزوّد حين يختلف eventDate (§8-ك) ──
const c0 = uat.indexOf("const CAP_KIND"), c1 = uat.indexOf("function impliedEpsAnnual");
if (c0 < 0 || c1 < 0) throw new Error("مرساة capNote مفقودة");
const esc = s => String(s);
const capNote = new Function("esc", uat.slice(c0, c1) + "\nreturn capNote;")(esc);
const nS = capNote({ capActions: [{ date: "2023-11-27", eventDate: "2026-04-21", factor: 0.666667, kind: "bonus" }] });
ok(nS.includes("2026-04-21") && nS.includes("عدّل المزوّد أسعارها حتى") && nS.includes("2023-11-27"),
   "capNote: بند الوصلة يذكر يوم المنحة وحدّ تعديل المزوّد");
const nP = capNote({ capActions: [{ date: "2026-10-01", factor: 0.833333, kind: "bonus" }] });
ok(nP.includes("الأسعار قبل") && !nP.includes("عدّل المزوّد"), "وبند عادي بالنص المعتاد");

// ── uat.html: capAdjPts — الشموع الخام تُحمل على أساس الإجراءات المطبَّقة في الرسم (§8-ق) ──
const a0 = uat.indexOf("function capAdjPts"), a1 = uat.indexOf("function chartPoints");
if (a0 < 0 || a1 < 0) throw new Error("مرساة capAdjPts مفقودة");
const capAdjPts = new Function(uat.slice(a0, a1) + "\nreturn capAdjPts;")();
const raw = [{ t: "2026-09-30", v: 14.54 }, { t: "2026-10-01", v: 12.11 }];
const adjp = capAdjPts({ capActions: [{ date: "2026-10-01", factor: 0.833333 }] }, raw);
ok(Math.abs(adjp[0].v - 14.54 * 0.833333) < 1e-9 && adjp[1].v === 12.11 && raw[0].v === 14.54,
   "capAdjPts: ما قبل الحدث × المعامل، وما بعده كما هو، والأصل لا يُمسّ");
ok(capAdjPts({}, raw) === raw, "وبلا capActions تعود الشموع كما هي");

console.log("\n" + (fail ? "❌ " : "✅ ") + pass + " نجحت، " + fail + " فشلت");
process.exit(fail ? 1 : 0);
