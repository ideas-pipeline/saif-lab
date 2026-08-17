# مصفوفة المطابقة — criteria v3 (المتطلب ↔ نقطة سهمك ↔ الحقل المكتوب)

**المرجع:** docs/requirements-v3.md | **المنفذان:** `scripts/fetch-inputs-sahmk.py` (sahmk-direct-v3) و`scripts/scoring-engine.py` (v2.0). تُراجع من وكيل الاستثمار قبل أول تشغيلة تكتب (§9-3).
**قرار معماري معلن:** منطق compute-valuation **مدموج في المحرك** — P/E وP/B والعائد تُحسب يومياً بالسعر الحي، وكل الوسطاء (تقييم + هامش الجودة + عائد 6م) في مكان واحد لحظة التقييم = صفر انزياح بينها وبين مستهلكيها. `compute-valuation.py` صار stub يخرج 0.

## 1. المتطلب ← المصدر ← الحقل

| متطلب الوثيقة | نقطة سهمك (المؤكدة) | الحقل المكتوب | التكرار | بوابة تشغيلة أولى |
|---|---|---|---|---|
| السعر وdailyChange (§6-5: من change_percent مباشرة، لا previous_close) | `/quotes/?identifiers=` (دفعات 50) | `currentPrice`, `dailyChange` (حارس ±11%), `volume`, `netLiquidity`, `priceUpdatedAt` | يومي | — |
| كل الفنية اليومية + مخزن الشموع التزايدي + **Z-الامتداد اليومي (§3.4 — قرار محلل 05-08 بعد حقيقة العمق)** | `/historical/{sym}/?interval=1d` — تأسيس 2600 يوم ثم تزايدي من آخر مخزن (`candles/{sym}.json`)؛ **الشمعة الجزئية ليوم التداول الجاري تُستبعد** (أعلام is_final/partial، وإلا قاعدة الوقت: شمعة بتاريخ اليوم قبل ~15:10 الرياض) | `dailyExtra{lastClose, lastDate, ema50d, rsi14d, macdD, macdSignalD, macdHistD, atr14, atrPct, high52wClose, low20Close, avgVol20, avgVol50, tradingValueMedian20, sessions, zExt, zObs, sma200d}` — ‏Z على المعدل: نافذة ≤756، حد أدنى 100 مشاهدة (≈300 جلسة)، pstdev، سقف ±10 | يومي | **توزيع العمق يُطبع كل تشغيلة** (وسيط/أدنى/أعلى الأسابيع + ≥200/≥240، ووسيط الجلسات + ≥300) — قادرو Z المتوقعون ≈ ذوو ≥300 جلسة |
| الأسبوعية المشتقة محلياً (§6-1) | مشتقة من 1d المعدل — أسبوع أحد-خميس، إغلاق=آخر جلسة، أسابيع مكتملة فقط (آخر مجموعة تسقط دوماً) | `weeklyTechnical{sma200w, ema40w, rsi14w(Wilder), macdW, macdSignalW(EMA9), macdHistW, sma200wSlope, priceRef, weeks, derived:true}` — ‏**zExt/zObs انتقلا إلى dailyExtra** (قرار محلل 05-08) | يومي | نسبة الشموع بلا adjusted_close ≈ 0 (تسقط من السلسلة المعدلة — تُعد `adj_dropped_rows`) |
| بوابة السيولة ≥1م ريال (§2) | وسيط (حجم×إغلاق خام) لآخر 20 جلسة من 1d | `liquidityGate{valueSar, threshold:1000000, passed}` (جذر السهم — عقد الواجهة القائم) | يومي | — |
| القوة النسبية خام/سعري (§3.3) بنوافذ 3م/6م/12-1 | 1d خام + `historical/TASI` | `relativeStrength{return3m, return6m, return12_1, rsTasi3m, rsTasi6m, rsTasi12_1, basis}` | يومي | — |
| جودة: نسب | `/analytics/ratios/{sym}/?history=latest&period=annual&metrics=core` (**core** — درس 04-08ج) بتفكيك مرن (قائمة جذرية/قاموس) | `financials{profitMargins, returnOnEquity, returnOnAssets, operatingMargin, debtToEquity}` | أسبوعي | شكل استجابة core (القائمة الجذرية مرصودة «بلا معاملات» — التفكيك يقبل الشكلين) |
| جودة: نمو + نقد + ميزانية (§6-4) | `/financials/{sym}/` بلا معاملات — آخر سنة كاملة، والنمو من سنتين متتاليتين فعلاً | `financials{revenueGrowth, ocf, fcf, netIncome, totalAssets, totalLiabilities, equity, ocfLiabilities(Beaver), equityAssets(رفع البنوك), fiscalYear, reportDate, cfReportDate}` | أسبوعي | — |
| حقوق الملكية (§6-8أ) | صريح إن حضر ≥90% ووسيط فرقه عن (أصول−مطلوبات) <2%، وإلا derived — يثبت | `data.equitySource{choice, presentPct, medianDiffPct, checkedAt}` | أول كاملة | **بوابة نصية**: قرار equitySource يُطبع ويُراجع |
| مقياس D/E (§6-8ب) | وسيط مقطعي على الكون الكامل — يثبت ويعاد استخدامه في --symbols | `data.deScaleDecision{scale, median, n, decidedAt}` | أول كاملة | مراجعة الحسم المطبوع مقابل 3 شركات معروفة |
| تقييم: مدخلات (§3.5) | `/company/{sym}/` fundamentals: ‏eps (eps_ttm وإلا eps)، book_value، pe (حارس تقاطع)، beta | `valuationInputs{eps, bookValue, peSource, beta, companyAsOf}` | أسبوعي | **اصطلاح eps** (‏ttm؟) يُراجع يدوياً لرمزين + حارس تقاطع pe يعد في `valuation.peSourceDiffPct` وL1 [6] |
| تقييم: محسوب يومياً | المحرك: ‏pe=السعر/eps ‏(0<pe≤500 وإلا رفض؛ خاسرة→null→0 عمداً)، pb=السعر/book_value ‏[0.05،50]، dy=divTtm12m/السعر | `valuation{pe, pb, dividendYield, peSourceDiffPct}` | يومي (محرك) | — |
| عائد التوزيعات (§6-6) | `/dividends/{sym}/` — مجموع 12 شهراً بتاريخ الاستحقاق | `valuationInputs{divTtm12m, divBasis(ttm12m/none-recent18m/none), divsAsOf}` | أسبوعي | — |
| sector/industry — العمود الفقري (§7) | `/company/` ‏sector/industry | جذر السهم + `data.sectorChanges[]` عند التغير (إنذار L1 [5]) | أسبوعي | **قيم التصنيف الفعلية** (عربية/إنجليزية؟) — المطابقة البنكية متسامحة (bank/بنك/مصرف) والعدد المطبوع متوقع ~10 |
| صيانة الكون (§7) | `/companies/` | مدرج جديد يُضاف؛ الغائب `delisted:true, delistedAt` + إغلاق توصياته المفتوحة `closeReason:"delisted"` في watchlist-config | شهري (‎--maintain-universe) | **شكل النقطة كله غير مؤكد** — فشلها يتخطى بلا إسقاط التشغيلة |
| نظام السوق (§2 — عرض ووسم فقط) | `historical/TASI` + `/market/summary/` | `marketRegime{}` (عقد v2.1 نفسه) + `tasi`, `tasiReturns{3m,6m,12_1}` | يومي | — |
| الوسطاء (§6-7) | المحرك محلياً من الكون الكامل غير المشطوب — P/E وP/B والعائد من الموجبة؛ الهامش وعائد 6م من الكل؛ قطاع <5 → بدائل (هامش: سلم مطلق؛ P/E وP/B: مرجع السوق — **غ-2 محسومة**) | `sectorMedians{sec:{peMedian, pePool, pbMedian, pbPool, divYieldMedian, marginMedian, marginPool, ret6mMedian, r6Pool, count}}` + `marketMedians` | يومي (محرك) | — |
| الحراس (§8) | الجالب (نمو/ميزانية/ROE/وحدات/تغير يومي) + المحرك (pe/pb) | `stock.guardRejected[{field, value, reason, date}]` — تعاد بناؤها كل تشغيلة | كل تشغيلة | — |
| بوابات الفشل (§7) | فشل >10% أي نوع / تاسي / انهيار تغطية (data.coverage) / انزياح جماعي — في الجالب؛ عناقيد P/B وتصنيفات >25% — في المحرك | خروج 1 **قبل الكتابة** في الحالتين | كل تشغيلة | — |

## 2. المحاور (المحرك — المقام 100 مباشرة)
كما في الوثيقة §3 حرفياً: جودة 30 (عام: نمو6+هامش-نسبي6+ROE6+D/E6+نقد6 | بنوك: ROA10+ROE8+هامش6+نمو6) + اتجاه 25 + قوة 15 (12-1/6م/قطاع6م/3م) + مخاطر 15 (ATR4+Z3+قيمة تداول3+حجم2+ملاءة3: ‏Beaver للعام/رفع رأسمالي للبنوك) + تقييم 15 (P/E6+P/B5+عائد4). التصنيف السباعي بعتبات 80/65/50/35 × توقيت طبقة الدخول (🟢=ممتاز، 🟡=مقبول، 🔴=انتظر، ⚪=محايد).
**غموضان محسومان بأقرب قراءة للنص (للمراجعة):** غ-1: إشارات ≥3 بلا الإشارة 1 → 🟡 بصياغة استعادة (الجدول لا يغطيها نصاً). غ-2: قطاع <5 في P/E وP/B → مرجع وسيط السوق موسوماً (البدائل المطلقة منصوصة للهامش فقط).

## 3. عقد الحقول للواجهة (وكيل UX — template.html لم يُمس)
كل سهم: `investmentScore{total(0-100), quality, trend, relativeStrength, risk, valuation, classification, classCode(strong_buy|buy|buy_wait|conditional_buy|hold|sell|strong_sell|unrated|filtered), filtered, unrated, filterReason, viaReversal, liquidityBlocked, timing, timingSignals, details{quality|trend|relativeStrength|risk|valuation|timing:[]}, topDrivers[{text,type}], criteriaVersion:"v3"}`.
**طبقة الدخول (الجديد كلياً):** `investmentScore.entry{state(green|yellow|red|neutral — الحالة الخام للتصنيف), displayState (بعد تكييف النظام الهابط — هو ما يُعرض), phrase (الجملة الجاهزة للمبتدئ — تُعرض كما هي، صيغت بقواعد §4 بما فيها «تقريباً» الملزمة ودلالة دخول/استعادة), signals, signalsAvailable, signalDetails[], referenceLevel, referenceLevelType(entry|reclaim), extensionAtr, nearHighWarning}`.
جذر السهم: `liquidityGate{valueSar, threshold, passed}` (شارة 💧 القائمة تعمل بلا تعديل)، `guardRejected[]`، `delisted/delistedAt`، `sector/industry` (قد تتغير قيمهما لتصنيف سهمك — بوابة أولى). الجذر العام: `marketRegime` (عقد v2.1)، `sectorMedians` (مفاتيح جديدة marginMedian/pePool…)، `coverage`, `equitySource`, `deScaleDecision`, `criteriaVersion`، **`runType/runTypeAt`** (قاعدة الإقفال الحصرية — شرط المحلل 2: ‏close|intraday بحد ~15:10 الرياض؛ المغذي وسكربتا الإغلاق يرفضان intraday أو الغائب)، **`scoringStats{counts, universe, at}`** (عقد الإحصاء الموحد — المحرك يخزن عدّه وL1 يعيد العدّ ويقارن؛ درس إنذارات 05-08ب الكاذبة: L1 قرأ ملفاً بائتاً في مساره الافتراضي — يُمرر المسار لـL1 صراحة في خط السيرفر).
**سلاسل الرسم (الموجة 1 — تفعيل الرسم التفاعلي؛ الرسم القديم يقرأ technical.chartPrices الميتة):** لكل سهم حقل `series{d30, d90, w52, w156, mAll}` — كل مدة `{start: "YYYY-MM-DD", p: [أرقام], iv?}` **بلا تواريخ لكل نقطة**؛ الواجهة تشتق التواريخ بالفهرس التقريبي من start:
- **d30/d90**: إغلاقات يومية **خام** — النقطة = جلسة تداول (الفهرس ≈ أيام عمل من start، لا أيام تقويمية).
- **w52/w156**: أسبوعية مشتقة **معدلة** (اصطلاح §6-1 نفسه — أسابيع مكتملة أحد-خميس، تتسق مع SMA200W للتراكب)؛ start = تاريخ آخر جلسة في أول أسبوع؛ النقطة = أسبوع.
- **mAll**: آخر إغلاق **خام** لكل شهر ميلادي للتاريخ كله (~7 سنوات)؛ `iv: "M"` — وقد تصير `"Q"` (ربع سنوية) إن فعّلت ميزانية الحجم التقليص؛ الشهر الجاري بآخر إغلاق متاح.
- **سلوك الغياب**: سهم بلا مخزن كافٍ → المدد المتاحة فقط (d30 عند ≥5 جلسات، d90 عند >30، w52 عند ≥8 أسابيع، w156 عند >52، mAll عند ≥6 أشهر) — تحقق من وجود المفتاح قبل الرسم؛ `series` كله قد يكون null. التقريب: منزلتان (وثلاث لسهم < 1 ريال). **الأحجام الفعلية المقيسة (مخزن 244):** الإجمالي 554KB مضغوطاً، والملف النهائي 2.40MB (الإخراج صار مضغوطاً بلا indent — قرار معلن). `levels` (دعم/مقاومة) يُضاف لاحقاً بمواصفة المحلل (TODO-SR).
**مستويات الدعم والمقاومة الإرشادية (§4-ب المختوم — عرض إرشادي محض، المحرك لا يقرأها):** لكل سهم حقل `levels`:
```
levels: {
  updatedAt, basis: "raw-capadj",           // السلسلة: خام معدل للإجراءات الرأسمالية فقط (§4-ب ش-1)
  since: "YYYY-MM-DD",                      // بداية التاريخ الفعلية — الوسم الصادق: «أعلى/أدنى المتاح (منذ {since})»
                                            // (نص الملحق مثّل بـ2022-06؛ المخزن الفعلي أعمق ~2019 — الوسم ديناميكي بمبدأ «الوسم لا يكذب»)
  price,                                    // السعر المرجعي وقت الحساب
  capActions?: [{date, factor}],            // الإجراءات المكتشفة (بوابة أولى: تحقق يدوي)
  restricted?: true, restrictedFrom?,       // الحارس ب: كشف ملتبس → النافذة مقيدة + إنذار L1
  insufficientHistory?: true, note?,        // < 250 جلسة → الكبرى فقط أو «التاريخ غير كافٍ لمستويات موثوقة»
  majors?: {high52, low52, maxAvail, minAvail},  // high52 بأعلى high موسومة «قمة 52 أسبوعاً (أعلى سعر متداول)»
                                            // — تعمداً غير موحدة مع high52wClose (أعلى إغلاق) في طبقة الدخول: غرضان معلنان، لا تُعرضا رقماً واحداً
  supports: [zone×≤2], resistances: [zone×≤2],   // أقرب اثنين من كل جانب، الأقرب أولاً — **نطاقات لا أرقام**
  inside?: zone,                            // «السعر داخل منطقة تقريبية الآن» — لا تُعد ضمن الدعمين/المقاومتين
  noResistanceAbove?: true,                 // «لا مقاومة معروفة فوق السعر (عند أعلى المتاح)» — يتكامل مع تحذير قرب القمة ولا يكرره
  noSupportBelow?: true,
  nearZone?: "support"|"resistance",        // سعر ضمن 1×ATR من حافة أقرب منطقة → جملة السياق الوحيدة «السهم قرب منطقة دعم تقريبية»
}
zone: {lo, hi, c, strength: "strong"|"medium", touches, tags: ["round"?, "volnode"?]}
```
قواعد العرض الملزمة: كل عرض بوسم **«مناطق تقريبية إرشادية — ليست ضماناً ولا توصية»** ولفظ «تقريبي» ملزم؛ الألوان المقترحة: strong أوضح من medium؛ 🔵 round / 📊 volnode / ⛰️ الكبرى؛ **المستوى المرجعي لطبقة الدخول يبقى السيد** — المناطق سياق رسم فقط، وعند تعارض بصري يُعرض الاثنان بوسميهما بلا توفيق آلي. مانع الرفرفة مطبق في الجالب (المعروض يثبت حتى ابتعاد المحسوب >1% عنه — المقارنة ضد المعروض المخزن في الملف). **الحجم الفعلي المقيس: ‏levels ‏115KB + series ‏554KB = 669KB ≤ سقف 800 الشامل.**
**مفكرة التوزيعات وشارة المحفظة (عقد المحلل 14-08):** الجذر العام يكسب `upcomingDividends: [{sym, name, value, period, fy, annDate, eligDate|null, distDate|null}]` (مفروزة بأقرب حدث؛ نافذة 45 يوماً؛ `eligDate:null` تُعرض «الأحقية: لم تُعتمد بعد»؛ الكتلة قد تكون بائتة عند فشل الجلب — تحقق من `upcomingDividendsAt` واعرض عمره إن تجاوز يوماً) و`portfolioSymbols: [رموز]` (‏legacy الـ15 — شارة «في محفظتك»). **حقلا حراسة اختياريان على صف المفكرة (حادثة 2060/2080، ‏17-08):** `suspectDup: true` = توقيع الحدث {قيمة+تاريخين} مكرر عبر رموز والحامل شاذ الترجيح — **يُعرض بتحذير صريح «إسناد مشكوك فيه — قيد التحقق من المصدر» لا يُخفى**؛ `highYield: true` = عائد فردي >8% — شارة تنبيه «عائد استثنائي — تحقق». **عزل قياس ملزم**: الكتلة عرض محض — لا تدخل في divsSince ولا أي حساب دقة.
**تنبيه توافق للواجهة الحالية:** ‏`relativeStrength.rsTasi12_1` حل محل rsTasi12m، و`dailyExtra` فقد high52w/low52w القديمين لصالح `high52wClose/low20Close`، ولا `previousClose` بعد اليوم (§6-5)، و**Z انتقل من `weeklyTechnical.zExt` إلى `dailyExtra.zExt` (+`zObs`/`sma200d`) بإطاره اليومي** (قرار محلل 05-08) — تُعالج في ورشة UX.

## 4. بوابات التشغيلة الأولى (مجمعة)
1. **عمق 1d**: عمق سهمك المرصود يبدأ ~2022-06 (~210 أسابيع) — لا بوابة «≥240 أسبوعاً» بعد اليوم؛ بدلها **توزيع العمق يُطبع كل تشغيلة** (أسابيع: وسيط/أدنى/أعلى + ≥200/≥240؛ جلسات: وسيط + ≥300)، وقادرو Z المتوقعون ≈ ذوو ≥300 جلسة (Z يومي — قرار محلل 05-08).
2. **قيم sector/industry الفعلية** + عدد البنوك بالمطابقة المتسامحة = ~10.
3. **equitySource**: القرار المطبوع (presentPct/medianDiffPct) يراجع يدوياً؛ و**deScale** مقابل 3 شركات معروفة.
4. **اصطلاح eps** في company (ttm؟) لرمزين + توزيع `peSourceDiffPct` (فرق >10% عند >25 سهماً = شبهة اصطلاح — L1 [6]).
5. **/companies/** شكلها كله (الصيانة تتخطى بأمان إن فشلت).
6. **adj_dropped_rows ≈ 0** وإلا مراجعة اصطلاح المعدل.
7. **توزيع النقاط الافتتاحي** (§9-2): يُقرأ وصفياً أسبوعين بلا أي تعديل عتبات — L1 [8] يطبعه.
7-ب. **الإجراءات الرأسمالية المكتشفة (§4-ب ش-1 — ملزمة):** الجالب يطبع كل المكتشفين (رمز/تاريخ/عامل) كل تشغيلة — التحقق اليدوي لسهم واحد معروف المنحة مقابل إعلانات تداول (المرصود في مخزون المختبر: 4322 بتاريخ 2023-05-03 عامل 0.7538 — مرشح الفحص)، والمقيدون (كشف ملتبس) يراجعون يدوياً بإنذار L1.
8. **خطوة التفعيل (ش-1 — بقرار مالك، لمرة واحدة):** أول تشغيلة محرك v3 على بيانات v2.1 تفجر بوابة التصنيفات >25% حتماً (مقيسة: 222/248) — التفعيل: `python3 scripts/scoring-engine.py stocks-data.json --activation` — يتخطى بوابتي التصنيفات وعناقيد P/B لهذه التشغيلة فقط بطباعة صارخة، ويسجل `data.activationEvent{version, date, classChanged, note}` (قطع العينة الموسوم)، ويرفض العمل إن كانت v3 مفعلة أصلاً. كل التشغيلات اللاحقة بلا العلم والبوابات كاملة السلطة.
   - **حارس عقد v3 (درس حادثة 05-08):** المحرك يرفض أي ملف بعقد قديم قبل كل شيء **حتى مع --activation** — البصمة: بين ذوي `dailyExtra` غير الفارغة، حاملو `dailyExtra.lastClose` و`relativeStrength.return12_1` معاً <50% → خروج 1 «الملف بعقد قديم (v2.1) — شغّل الجالب v3 أولاً». (الحادثة: الجالب انهار قبل الكتابة فاستُهلك التفعيل على ملف v2.1.)
   - **`--reset-activation` (بقرار مالك):** يبطل `activationEvent` مستهلَكاً على بيانات فاسدة (كتابة ذرية، طباعة موسومة بتاريخ الحدث المبطَل) ليُتاح تفعيل نظيف: تشغيلة جالب v3 ناجحة ← `--reset-activation` ← `--activation`. ملف بلا حدث → خروج 1.
