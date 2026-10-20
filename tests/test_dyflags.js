const fs = require("fs");
const { loadDyFlags, stocksOf } = require("./harness.js");
const path = require("path");
const ROOT = process.env.REPO || path.resolve(__dirname, "..");
const HTML = process.argv[2] || ROOT + "/uat.html";
let pass = 0, fail = 0;
const ok = (c, m) => { c ? pass++ : (fail++, console.log("  ❌ " + m)); };
const eq = (a, b, m) => ok(JSON.stringify(a) === JSON.stringify(b), m + "\n     توقع: " + JSON.stringify(b) + "\n     وجد : " + JSON.stringify(a));

/* REPO يسمح بتشغيل الحزام نفسه على مستودع محاكاة — فلا نسخة ثانية من الحزام
   (النسخة الثانية هي التي كانت تطمس ملف الأساس المشترك). */
const REPO = ROOT;
/* البيانات مثبتة على لقطة من تاريخ main (harness.pinnedDataPath): التأكيدات بأسماء
   الأسهم تحرس **الكود**، والبيانات الحيّة تنتقل كل أسبوع (19-10). وما يراقب البيانات
   نفسها يقرأ الحيّ صراحةً (LIVE أدناه). */
const PD = require("./harness.js").pinnedDataPath(REPO);
const { DATA, stocks } = stocksOf(PD.path);
console.log("البيانات: " + PD.label);
const dyFlags = loadDyFlags(HTML, DATA);
/* الأساس يُحسب حيّاً من **كود** مرجعٍ مختوم على *البيانات المثبتة نفسها* — لا من لقطةٍ
   لِمُخرَج الأساس، **ولا من HEAD** (فذاك يصير مقارنةَ الملف بنفسه لحظةَ الإيداع — عيب أثبته ختم 05-10).
   المرجع الافتراضي origin/main: آخر ما ختمه الناقد، وهو خارج الفرع فلا يتحرك معه. */
const { loadBaseline } = require("./harness.js");
const BASE_REF = process.env.BASE_REF || "origin/main";
const B = loadBaseline(REPO, BASE_REF, DATA, HTML);
const dyFlagsHEAD = B.fn;
console.log("أساس المقارنة: " + B.ref + " (" + B.sha + ")  بصمة dyFlags: أساس " +
            B.baseHash + " · مُختبَر " + B.testHash);
if (B.identical) console.log("⊘ المقطعان متطابقان بايتاً — تأكيدات الدلتا (4 و5 و5أ) **لاغية**: لا فرق كود لتُقاس عليه.");
let vacu = 0;
const vac = (m) => { vacu++; console.log("  ⊘ " + m + " — لاغية (لا فرق كود)"); };
const before = {}; let bWith = 0, bTotal = 0;
for (const s of stocks) { const g = dyFlagsHEAD(s); before[s.symbol] = g; if (g.length) bWith++; bTotal += g.length; }

const FLIP = "أساسان مختلفان للربح", LOSS = "أُقفلت بخسارة", NOPROFIT = "أُقفلت بلا ربح";
const after = {}, gFlip = [], gLoss = [];
let withFlag = 0, total = 0; const counts = {};
for (const s of stocks) {
  const f = dyFlags(s); after[s.symbol] = f;
  if (f.length) withFlag++; total += f.length;
  for (const x of f) { const k = x.slice(0, 26); counts[k] = (counts[k] || 0) + 1; }
  if (f.some(x => x.includes(FLIP))) gFlip.push(s.symbol);
  if (f.some(x => x.includes(LOSS) || x.includes(NOPROFIT))) gLoss.push(s.symbol);
}
console.log("── تأكيدات dyFlags (بعد ختم الناقد) ──");

// ١ اختبار الصلابة أسقط 7200
eq(gFlip.sort(), ["4012","4180","4194","4292","6014"], "1) وسم تعارض الأساس = خمسة (7200 أسقطه اشتراط العددين)");
ok(!after["7200"].some(x => x.includes(FLIP)), "1أ) 7200 بلا وسم تعارض");
// ٢ فرع الخسارة صار حياً ومستقلاً
/* التأكيدات 2 و2ز و2ح على **اللقطة المثبتة** (8368b07)، فلم تعد تعضّ عند جلبٍ جديد
   كما قرّر §8-ظ (08-10). وقد عضّت فعلاً يوم 19-10 بغير ما تنبّأ به: قطع 8 · تعارض 0
   لا 4 · 4 — بندٌ مفتوح للمحلل في docs/implementation-notes.md. فإن أُريد قياسُ
   الانتقال على بيانات اليوم: DATA_REF=origin/main. */
eq(gLoss.sort(), ["2010","2310","4144"], "2) القطع بالخسارة = الثلاثة الذين يوافقهم سجلهم");
const gCont = stocks.filter(s => dyFlags(s).some(x => x.includes("أساسان متعارضان للربح"))).map(s => s.symbol).sort();
eq(gCont, ["2170","2250","2282","2290","3050"], "2ز) «أساسان متعارضان» = الخمسة الذين تعارضهم حقول كتلتهم");
ok(dyFlags(stocks.find(s => s.symbol === "2250")).some(x => x.includes("متعارضان") && !x.includes("الهامش الصافي")),
   "2ح) 2250 يسمّي الحقلين المعارضين فقط (هامشه 0.0 لا موجب)");
/* ١١ حارس حياة للشاهدين المستقلّين — **صناعي لا جمهوري** (محدَّث 08-10).
   الغرض باقٍ: منذ أن صار ROE وROA يُحسبان عندنا من netIncome، لو قرأ الوسمُ الحقلَ
   المحسوب بدل حقل المزوّد المحفوظ لصار اتفاقُهما مع netIncome متطابقةً رياضية — أي
   شاهدين ميتين بالبناء يمرّان صامتَين.
   لكن الشرط كان «حيٌّ على ≥20 سهماً حقيقياً»، وقد **استجاب المزوّد وأصلح أساسه
   (08-10)** فصارت قيمه تطابق حسابنا ⇒ الجمهور الحقيقي يهبط إلى صفر **بحق**. فشرطٌ
   على الجمهور كان سيُرسِب الحزام على خبرٍ سارّ.
   فصار الشرط على سهمٍ **صناعي**: يثبت أن الفرع **قابل للإطلاق** متى عاد التباين —
   على نسق حارس DY_EXTREME_PCT في هذا الملف. والجمهور الحقيقي يُطبع **خبراً لا
   تأكيداً**، فيُرى انهياره ولا يُرسِب. */
{
  /* الجمهور الحقيقي وأرضية الحضور سؤالان عن **البيانات** لا عن الكود ⇒ يقرآن الحيّ
     (شرط ختم 19-10): على لقطة مجمّدة كانا يطبعان رقماً ميتاً ولا يرسبان أبداً. */
  const LIVE = JSON.parse(fs.readFileSync(require("./harness.js").liveDataPath(REPO), "utf8")).stocks;
  const neg = LIVE.filter(s => ((s.financials || {}).netIncome || 0) < 0);
  const wit = k => neg.filter(s => typeof (s.financials || {})[k + "Src"] === "number" &&
                                   s.financials[k + "Src"] > 0).length;
  console.log("  ℹ️ الجمهور الحقيقي للشاهد المستقل (بيانات حيّة): ROE " + wit("returnOnEquity") +
              " · ROA " + wit("returnOnAssets") + " سهماً خاسراً (خبر لا تأكيد — " +
              "يهبط إلى صفر بحقٍّ متى اتفق المزوّد مع القوائم)");
  /* وأرضية حياة على **حضور** قيمة المزوّد لا على موجَبيّتها (شرط ختم 08-10):
     الموجَبيّة تموت باتفاقهم بحق، أما الحضور فلا يموت إلا بالعطب — توقّفِهم عن
     الإرسال، أو طمسِ أنبوبنا قيمتَهم بحسابنا (عطب 06-10). فهذا هو السؤال الباقي. */
  const present = k => LIVE.filter(s => typeof (s.financials || {})[k + "Src"] === "number").length;
  ok(present("returnOnEquity") >= 200,
     "11ب) المراقِب حاضر (بيانات حيّة): قيمة المزوّد لـROE على " + present("returnOnEquity") + " سهماً (أرضية 200)");
  ok(present("returnOnAssets") >= 200,
     "11ج) وROA على " + present("returnOnAssets"));
  // سهم صناعي: خسارةٌ معلنة وحقلا مزوّدٍ موجبان ⇒ الفرع يجب أن ينطق بهما
  const x = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === "2250")));
  x.financials.netIncome = -1000; x.financials.profitMargins = null;
  x.financials.returnOnEquitySrc = 7.7; x.financials.returnOnAssetsSrc = 3.3;
  x.financials.returnOnEquity = -5.0; x.financials.returnOnAssets = -2.0;
  const f11 = dyFlags(x).find(y => y.includes("متعارضان")) || "";
  ok(f11.includes("العائد على حقوق الملكية") && f11.includes("العائد على الأصول"),
     "11) الفرع قابل للإطلاق: شاهدا مزوّدٍ موجبان مع خسارة ⇒ يُسمّيان — " + f11);
  // والضابطة: الحقل المحسوب وحده لا يُطلقه (إثبات أنه يقرأ *Src لا المحسوب)
  const y = JSON.parse(JSON.stringify(x));
  delete y.financials.returnOnEquitySrc; delete y.financials.returnOnAssetsSrc;
  ok(!dyFlags(y).some(z => z.includes("متعارضان")),
     "11أ) وبلا حقول مزوّد لا ينطق — فهو يقرأ *Src لا المحسوب");
}
ok(!gCont.some(x => gLoss.includes(x)), "2ط) الفئتان متنافيتان");
ok(after["2010"].some(x => x.includes("خسارة (8.59 ريال للسهم)")), "2أ) سابك: نص الخسارة بالمبلغ — " + JSON.stringify(after["2010"]));
ok(after["2290"].some(x => x.includes("أساسان متعارضان")) && after["2290"].some(x => x.includes("التوزيع أكبر من ربح")),
   "2ب) ينساب: نسبة لا قطع، مع وسم التغطية — " + JSON.stringify(after["2290"]));
// ٣ نص 4194
eq(after["4194"].find(x => x.includes(FLIP)),
   "التوزيع داخل ربح 12 شهراً (0.90×) ويتجاوز ربح 2025 الكامل المعلن (2.14×) — أساسان مختلفان للربح، تحقّق قبل الاعتماد",
   "3) نص 4194 الكامل");
// ٤ تفوُّق لكل سهم
const lost = [];
for (const s of stocks) for (const o of (before[s.symbol] || [])) if (!after[s.symbol].includes(o)) lost.push(s.symbol + ": " + o);
/* ٤) هذه الموجة **تغيّر** خرج dyFlags بقصد: الوسم صار يقرأ حقل المزوّد المحفوظ
   (*Src) بدل الحقل المحسوب، فيعود الشاهدان المستقلان. فلا يصحّ تأكيد «دلتا صفر»
   هنا — ولا يصحّ تمييعه. والمؤكَّد هو **شكل الدلتا بعينه**: لا سهم يخرج من فئته،
   ولا يفقد وسماً إلا ليكسب نسخةً أغنى منه تسمّي شهوداً أكثر. */
const OPPO = "أساسان متعارضان";
if (B.identical) vac("4) لا سهم يفقد وسماً قائماً");
else {
  const bad = [];
  for (const s of stocks) {
    for (const o of (before[s.symbol] || [])) {
      if (after[s.symbol].includes(o)) continue;
      const nw = after[s.symbol].find(x => x.slice(0, 20) === o.slice(0, 20));
      const richer = o.includes(OPPO) && nw && nw.length > o.length;
      /* والاتجاه الثاني المسموح: قطعٌ قاطع يعود **نسبةً** — أي الوسم يصير أقلّ
         حكماً لا أكثر، وهو عين مبدأ الموجة (ننسب ولا ندّعي). العكس ممنوع. */
      const softer = (o.includes(LOSS) || o.includes(NOPROFIT)) &&
                     after[s.symbol].some(x => x.includes(OPPO));
      if (!richer && !softer) bad.push(s.symbol + ": " + o);
    }
  }
  eq(bad, [], "4) لا سهم يفقد وسماً إلا ليكسب نسخةً أغنى منه (وسم التعارض يسمّي شهوداً أكثر)");
  /* (4أ و4ب حُذفا — ختم 20-10، بند 12): كانا شكلَ دلتا موجة الشهود 06-10 بعينها
     (الأغنياء 2170/2282/2290/3050، ويلين 2250). وبعد دمجها صار الأساس يحملها، فأي موجة
     لاحقة تغيّر الخرج كانت ستُطالَب بدلتا 06-10 فتسقط زوراً. والتأكيد العام 4 أعلاه باقٍ. */
}
// ٥ المجاميع والقواعد الخمس
if (B.identical) vac("5) دلتا الكود صفر");
else eq([withFlag - bWith, total - bTotal], [0, 0],
   "5) المجاميع ثابتة: التغيير يُغني نصوصاً ولا يُنشئ وسماً ولا يُلغيه");
const RULES = ["التوزيع أكبر من ربح 12 شهراً", "يوزّع بلا ربح معلن", "السعر أدنى من متوسطه الطويل", "بلا سجل دفعات ولا قاعدة 200", "ضعف وسيط قطاعه أو أكثر"];
const nRule = p => stocks.filter(s => after[s.symbol].some(x => x.startsWith(p))).length;
const nRuleHEAD = p => stocks.filter(s => dyFlagsHEAD(s).some(x => x.startsWith(p))).length;
if (B.identical) vac("5أ) القواعد الخمس القائمة");
else eq(RULES.map(nRule), RULES.map(nRuleHEAD), "5أ) القواعد الخمس القائمة: مطابقة لكود الأساس على نفس البيانات");
// ٦ سلامة
const dirty = [];
for (const s of stocks) for (const x of after[s.symbol]) if (/NaN|Infinity|undefined|null/.test(x)) dirty.push(s.symbol + ": " + x);
eq(dirty, [], "6) لا NaN/Infinity/undefined/null في أي سلسلة");
// ٧ السنة من البيانات
const c = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === "4194"))); c.financials.fiscalYear = null;
const fb = dyFlags(c).find(x => x.includes(FLIP));
ok(fb && fb.includes("آخر ربح سنوي كامل معلن"), "7) fiscalYear=null → نص احتياطي: " + fb);
const c2 = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === "2010"))); c2.financials.fiscalYear = null;
ok(dyFlags(c2).some(x => x.includes("آخر سنة مالية كاملة معلنة")), "7أ) وفرع الخسارة كذلك");
// ٨ التدهور
const deg = (sym, mut, wantFlip, wantLoss, label) => {
  const x = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === sym))); mut(x);
  let f; try { f = dyFlags(x); } catch (e) { fail++; return console.log("  ❌ 8) استثناء " + label + ": " + e.message); }
  ok(f.some(y => y.includes(FLIP)) === wantFlip && f.some(y => y.includes(LOSS) || y.includes(NOPROFIT)) === wantLoss,
     "8) " + label + " → " + JSON.stringify(f));
};
deg("4194", x => x.financials.netIncome = null, false, false, "بلا netIncome");
deg("4194", x => x.valuationInputs.sharesOutstanding = 0, false, false, "أسهم=0");
// ربح سالب على سهم هوامشه موجبة → نسبة لا قطع (وهو عين المطلوب)
{ const x = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === "4194"))); x.financials.netIncome = -1;
  ok(dyFlags(x).some(y => y.includes("أساسان متعارضان")), "8) ربح سالب وهوامش موجبة → نسبة لا قطع"); }
// وبإسكات الحقول المعارضة يعود القطع
{ const x = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === "4194"))); x.financials.netIncome = -1;
  /* الإسكات يشمل حقول المزوّد المحفوظة لأن الوسم يقرؤها هي (ختم 06-10) */
  for (const k of ["profitMargins", "returnOnEquity", "returnOnAssets",
                   "returnOnEquitySrc", "returnOnAssetsSrc"]) x.financials[k] = null;
  ok(dyFlags(x).some(y => y.includes(LOSS)), "8أ) وبلا حقول معارضة يعود القطع بالخسارة"); }
deg("4194", x => x.financials.netIncome = 0, false, true, "ربح صفر → «بلا ربح»");
deg("4194", x => { delete x.valuationInputs.marketCap; }, true, false, "بلا marketCap → يُفشَل مفتوحاً فيصمد الوسم");
// ٩ فرع الخسارة مُعلَّق على netIncome وحده — لا يُسكته عدد أسهم غائب أو مخطوء
const lossOf = (sym, mut) => { const x = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === sym))); if (mut) mut(x);
  const g = dyFlags(x); return { has: g.some(y => y.includes(LOSS)), txt: g.find(y => y.includes(LOSS)) || "" }; };
ok(lossOf("2010").txt.includes("(8.59 ريال للسهم)"), "9) سابك: الرقم للسهم حاضر");
ok(lossOf("2010", x => delete x.valuationInputs.sharesOutstanding).has, "9أ) بلا عدد أسهم: الخبر يصمد");
ok(!lossOf("2010", x => delete x.valuationInputs.sharesOutstanding).txt.includes("ريال للسهم"), "9ب) ويُحجب الرقم وحده");
ok(lossOf("2010", x => { x.valuationInputs.sharesOutstanding = x.valuationInputs.marketCap / x.valuationInputs.theirPrice * 2; }).has,
   "9ج) عدد أسهم مخطوء 100%: الخبر يصمد");
ok(!lossOf("2010", x => x.financials.netIncome = null).has, "9د) بلا netIncome: يصمت (وهو ما يرصده حارس L1)");
ok(lossOf("2010", x => x.financials.netIncome = -0.000001 * x.valuationInputs.sharesOutstanding).txt.includes("أقل من 0.01"),
   "9هـ) خسارة ضئيلة: أرضية عرض بدل «0 ريال»");

/* ١٠ حارس حياة لفرع «عائد استثنائي» (شرط ختم 05-10ب): الفرع محجوب بـ!f.length
   وأعلى العوائد موسومةٌ أصلاً، فهو يُطلق على **صفر سهم** اليوم — فلو غُيّر الحدّ
   DY_EXTREME_PCT أو انكسر الفرع لمرّ صامتاً. وهو عين صنف «فرع الخسارة بلا حارس
   حياة» الذي كشفه ختم 03-10. فيُبنى سهمٌ صناعي نظيفٌ من كل وسم آخر. */
{
  /* سهمٌ صناعي مُسكَتةٌ فيه كل الفروع الأخرى بشروطها المصرَّحة في الكود:
     تغطيةٌ مريحة (dv ≪ eps) · ربح سنوي موجب · متوسط 200 أسبوع حاضر والسعر فوق
     75% منه (فيَسكت وسم الهبوط ووسمُ «بلا سجل») · وقطاعٌ بلا وسيط (فيَسكت وسم
     ضعف الوسيط). ثم العائد وحده يحرّك الحكم. */
  const mk = dy => {
    const x = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === "4194")));
    x.sector = "قطاع-صناعي-بلا-وسيط";
    x.financials = { ...x.financials, netIncome: 9e11, fiscalYear: 2025 };
    x.valuationInputs = { ...x.valuationInputs, eps: 100, divTtm12m: 1, sharesOutstanding: 1e6 };
    x.weeklyTechnical = { ...(x.weeklyTechnical || {}), sma200w: 1 };
    x.currentPrice = 100; x.dailyExtra = { ...(x.dailyExtra || {}), lastClose: 100 };
    x.valuation = { ...(x.valuation || {}), dividendYield: dy / 100 };
    return x;
  };
  const at12 = dyFlags(mk(12)), at8 = dyFlags(mk(8)), EX = "عائد استثنائي";
  ok(at12.length === 1 && at12[0].includes(EX),
     "10) حارس حياة: عائد 12% نظيفٌ من كل وسم ⇒ «عائد استثنائي» وحده — " + JSON.stringify(at12));
  ok(!at8.some(x => x.includes(EX)),
     "10أ) وعائد 8% لا يُطلقه فالحدّ 10% فعّال — " + JSON.stringify(at8));
}

/* ١١ §8-ق: بعد منحة/تجزئة مطبَّقة يصير التوزيع والسعر على أساس السهم الحالي، ويُقسم عدد
   الأسهم المجمّد (ولقطة القيمة السوقية) على sharesCapFactor — فالوسوم لا تتغيّر بالإجراء
   نفسه. سهمٌ بمنحة 1:1 على 4194 و2290: كل ما هو للسهم ÷2 والعدد المجمّد كما هو. */
for (const sym of ["4194", "2290"]) {
  const x = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === sym)));
  const y = JSON.parse(JSON.stringify(x));
  const half = v => (typeof v === "number" ? v / 2 : v);
  y.valuationInputs.sharesCapFactor = 0.5;
  for (const k of ["divTtm12m", "eps"]) y.valuationInputs[k] = half(y.valuationInputs[k]);
  y.currentPrice = half(y.currentPrice);
  if (y.dailyExtra) y.dailyExtra.lastClose = half(y.dailyExtra.lastClose);
  if (y.weeklyTechnical) y.weeklyTechnical.sma200w = half(y.weeklyTechnical.sma200w);
  eq(dyFlags(y), dyFlags(x), "11) §8-ق " + sym + ": منحة 1:1 مطبَّقة لا تغيّر الوسوم (العدد ÷ sharesCapFactor)");
  /* حارس حياة على 4194 (وسمه نصٌّ بنسبة التغطية، فيتحرّك بالعدد)؛ ووسم 2290 لا يعبر عتبةً
     بخطأ العدد فلا يصلح شاهداً هنا */
  if (sym === "4194") {
    const z = JSON.parse(JSON.stringify(y)); delete z.valuationInputs.sharesCapFactor;
    ok(JSON.stringify(dyFlags(z)) !== JSON.stringify(dyFlags(x)),
       "11أ) §8-ق 4194: وبلا sharesCapFactor تنحرف — فالقسمة فعّالة لا زينة");
  }
}

/* ١٢ §8-م: eps مشتق من القوائم (حارس المزوّد) ⇒ وسم التغطية يسمّي ربح السنة الكاملة لا 12 شهراً */
{
  const x = JSON.parse(JSON.stringify(stocks.find(s => s.symbol === "4194")));
  x.valuationInputs.eps = 0.01;
  const tA = dyFlags(x).find(t => t.startsWith("التوزيع أكبر من"));
  x.valuationInputs.epsBasis = "fy-derived"; x.financials.fiscalYear = 2025;
  const tB = dyFlags(x).find(t => t.startsWith("التوزيع أكبر من"));
  ok(tA && tA.includes("ربح 12 شهراً") && tB && tB.includes("ربح 2025 الكامل") && !tB.includes("12 شهراً"),
     "12) §8-م: eps المشتق ⇒ «ربح 2025 الكامل» — " + tB);
}

console.log("\n" + (fail ? "❌ " : "✅ ") + pass + " نجحت، " + fail + " فشلت" +
            (vacu ? "، " + vacu + " لاغية" : ""));
process.exit(fail ? 1 : 0);
