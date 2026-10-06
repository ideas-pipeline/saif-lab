const fs = require("fs");
const path = require("path");
const ROOT = process.env.REPO || path.resolve(__dirname, "..");
const HTML = ROOT + "/uat.html";
const src = fs.readFileSync(HTML, "utf8");
const data = JSON.parse(fs.readFileSync(ROOT + "/stocks-data.json", "utf8"));
const stocks = data.stocks;
const a = src.indexOf("const DY_EXTREME_PCT"), b = src.indexOf("function dyCell");
const base = src.slice(a, b);
const pre = [/^const secOf=.*$/m, /^const dyOf=.*$/m, /^const fmt=.*$/m].map(re => src.match(re)[0]).join("\n") + "\n";
const FLIP = "أساسان مختلفان للربح";
const flagged = code => {
  const fn = new Function("DATA", pre + code + "\nreturn dyFlags;")(data);
  return stocks.filter(s => fn(s).some(x => x.includes(FLIP))).map(s => s.symbol).sort();
};
let pass = 0, fail = 0;
const eq = (x, y, m) => { JSON.stringify(x) === JSON.stringify(y) ? pass++ : (fail++, console.log("  ❌ " + m + "\n     توقع " + JSON.stringify(y) + "\n     وجد  " + JSON.stringify(x))); };
const FIVE = ["4012","4180","4194","4292","6014"], SIX = FIVE.concat("7200").sort();

console.log("── حساسية الثوابت واختبار الصلابة ──");
eq(flagged(base), FIVE, "الأساس = خمسة");

// اشتراط العددين هو ما يُسقط 7200 — لا عتبة مضبوطة
const robust = "    const robust=(ieB==null)||(ieB>0&&dv>ieB*COV_FLIP_MARGIN);";
if (!base.includes(robust)) { fail++; console.log("  ❌ سطر الصلابة غير موجود"); }
eq(flagged(base.replace(robust, "    const robust=true;")), SIX,
   "1) بإلغاء اشتراط العددين يعود 7200 → ستة (فالصلابة هي السبب لا العتبة)");

// حارس الأسهم 25% شبكة أمان لا مُرشِّح
const guard = 'if(typeof mc==="number"&&typeof tp==="number"&&tp>0&&Math.abs(mc/(sh*tp)-1)>0.25) return null;';
eq(flagged(base.replace(guard, "")), FIVE, "2) إزالة حارس 25% لا تغيّر المجموعة");

// الهامش: 1.00 يُرجع 7200 (صامد على العددين عندها)، و1.10 لا يُسقط أحداً من الخمسة
eq(flagged(base.replace("const COV_FLIP_MARGIN=1.05;", "const COV_FLIP_MARGIN=1.00;")), SIX, "3أ) عند 1.00 يعود 7200");
eq(flagged(base.replace("const COV_FLIP_MARGIN=1.05;", "const COV_FLIP_MARGIN=1.10;")), FIVE, "3ب) عند 1.10 الخمسة تصمد");

// فرع الخسارة مستقل فعلاً: إلغاء بوابة dv<=eps لا يغيّر عدد وسوم الخسارة
const fnBase = new Function("DATA", pre + base + "\nreturn dyFlags;")(data);
const lossN = stocks.filter(s => fnBase(s).some(x => x.includes("أُقفلت بخسارة") || x.includes("أُقفلت بلا ربح"))).length;
const contN = stocks.filter(s => fnBase(s).some(x => x.includes("أساسان متعارضان للربح"))).length;
eq([lossN, contN, lossN + contN], [4, 4, 8],
   "4) فرع الخسارة حيٌّ على الثمانية: قطعٌ لأربعة ونسبةٌ لأربعة (انتقل 2250 بتصحيح أساس النسب 06-10)");

// لا سنة صلبة
const blk = base.slice(base.indexOf("/* ‏(أ) خسارة السنة"), base.indexOf("if(wt.sma200w"));
eq((blk.match(/\b2025\b/g) || []).length, 0, "5) صفر ورود للسنة 2025 في الكتلة المُدرَجة");

console.log("\n" + (fail ? "❌ " : "✅ ") + pass + " نجحت، " + fail + " فشلت");
process.exit(fail ? 1 : 0);
