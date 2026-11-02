// §8-ق: وسم التصنيف الشرعي في الواجهة — بلا jsdom، يستخرج من uat.html نفسه.
// الاستخدام: node tests/test_sharia_ui.js
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) { pass++; console.log("  ✅ " + m); } else { fail++; console.log("  ❌ " + m); } };

const uat = fs.readFileSync(ROOT + "/uat.html", "utf8");
const a = uat.indexOf("let SHARIA={};"), b = uat.indexOf("async function boot(){");
if (a < 0 || b < 0 || b < a) throw new Error("مرساة الشرعي مفقودة في uat.html");
const pick = re => { const m = uat.match(re); if (!m) throw new Error("تعريف مفقود: " + re); return m[0]; };
const pre = [/^const esc=.*$/m, /^const secOf=.*$/m].map(pick).join("\n") + "\nconst fmt=(v,d=2)=>Number(v).toFixed(d);\n";
const mk = () => new Function(pre + uat.slice(a, b) +
  "\nreturn {set:v=>{SHARIA=v}, shariaOf, shariaNote, shariaBadge};")();
const F = mk();
const SH = JSON.parse(fs.readFileSync(ROOT + "/sharia.json", "utf8"));
F.set(SH);

const st = sym => ({ symbol: sym, sector: "Materials", industry: "" });
const bank = { symbol: "1120", sector: "Financials", industry: "Banks" };
let x = F.shariaOf(st("3005"));
ok(x.c === "pure" && x.label === "نقية" && x.p === 0, "3005: نقية، تطهير 0");
ok(F.shariaNote(x).includes("0.00 ريال للسهم") && F.shariaNote(x).includes("لقوائم 2025")
   && F.shariaNote(x).includes("لا يدخل تقييم سيف"), "التلميح: المبلغ بمنزلتين، السنة، «لا يدخل التقييم»");
ok(F.shariaBadge(st("2370")).includes('class="shr shr-mixed"') && F.shariaBadge(st("2370")).includes(">مختلطة<"),
   "2370: وسم «مختلطة» بلون الكهرماني");
ok(F.shariaBadge(st("2222")).includes(">جائزة<") && F.shariaNote(F.shariaOf(st("2222"))).includes("فقرة 18"),
   "أرامكو: «جائزة» مختصرة، والتفصيل (القطاع العام، فقرة 18) في التلميح");
ok(F.shariaBadge(st("1201")).includes("shr-non") && F.shariaBadge(st("1201")).includes(">غير متوافقة<"), "غير متوافقة");
x = F.shariaOf(bank);
ok(x.c === null && x.label === "—" && F.shariaNote(x).startsWith("البنوك خارج دراسة المقاصد"), "البنك: «—» مع تفسير الهيئات");
x = F.shariaOf(st("2210"));
ok(x.c === null && F.shariaNote(x) === "غير مشمول في دراسة المقاصد لقوائم 2025", "غير المشمول: «—» مع السنة");

// المتانة: بيانات غائبة أو مشوّهة لا تكسر الصفحة
F.set({});
ok(F.shariaOf(st("3005")).label === "—" && F.shariaNote(F.shariaOf(st("3005"))) === "التصنيف الشرعي غير متوفر حالياً",
   "ملف غائب ({}) ⇒ «—» «غير متوفر حالياً»");
F.set({ stocks: { "3005": { c: "halal", p: 1 }, "3060": { c: "pure", p: "x" } }, meta: {} });
ok(F.shariaOf(st("3005")).c === null && F.shariaOf(st("3060")).p === null, "تصنيف مجهول ⇒ «—»؛ مبلغ غير رقمي ⇒ يُحذف");
F.set({ stocks: {}, meta: {} });
ok(F.shariaOf({ symbol: "toString", sector: "x" }).c === null && F.shariaOf({ symbol: "__proto__", sector: "x" }).c === null,
   "مفاتيح النموذج الأولي لا تُقرأ تصنيفاً");
F.set({ stocks: { "9999": { c: "pure", p: 0.1 } }, meta: { study: 2025 } });
ok(!F.shariaBadge(st("9999")).includes("<script") && F.shariaBadge({ symbol: "9999", sector: "x" }).includes("data-tip=\""),
   "الوسم يمر عبر esc");

// المواضع: الجدول، بطاقة الجوال، رأس الدرج، خلية الدرج — ولا أثر في الفرز أو الفلاتر
ok(uat.includes('${esc(secAr(s))}${shariaBadge(s)}</span></span></td>'), "صف الجدول");
ok(uat.includes('${esc(secAr(s))}${shariaBadge(s)}</div></div>'), "بطاقة الجوال");
ok(uat.includes('${esc(s.industry)}`:""}${shariaBadge(s)}</div>'), "رأس الدرج");
ok(uat.includes('cell("التصنيف الشرعي"'), "خلية الدرج");
const sa = uat.indexOf("const SORTERS={");
ok(sa > 0 && !/sharia|SHARIA/.test(uat.slice(sa, uat.indexOf("};", sa))), "لا مفتاح ترتيب شرعي (SORTERS)");
const fa = uat.indexOf("function applyFilters("), fb = uat.indexOf("function sortList(");
ok(fa > 0 && fb > fa && !/sharia|SHARIA/.test(uat.slice(fa, fb)), "لا فلتر شرعي (applyFilters)");
const usesOutside = (uat.match(/shariaOf\(|shariaBadge\(|SHARIA\b/g) || []).length;
ok(usesOutside === 13, "مواضع الاستعمال محصورة (" + usesOutside + ")");

const tpl = fs.readFileSync(ROOT + "/template.html", "utf8");
ok(tpl.includes("return __SHARIA_DATA__;") && !tpl.includes('fetch("sharia.json"'), "القالب: مضمّن وقت البناء، لا fetch");

console.log("\n" + (fail ? "❌ " : "✅ ") + pass + " نجحت، " + fail + " فشلت");
process.exit(fail ? 1 : 0);
