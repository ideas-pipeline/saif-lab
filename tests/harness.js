// حزام اختبار dyFlags — يستخرج الدالة من المصدر المنشور نفسه ويحقن أقنعة نقية.
// لا jsdom: dyFlags دالة نقية متغيّراتها الحرّة DATA وdyOf وsecOf وfmt — وهذه
// الأربعة بعينها هي ما تُبصمه dySlice أدناه (عُدَّت من المصدر لا بالحدس).
const fs = require("fs");

function loadDyFlags(htmlPath, data) {
  const src = fs.readFileSync(htmlPath, "utf8");
  const a = src.indexOf("const DY_EXTREME_PCT");
  const b = src.indexOf("function dyCell");
  if (a < 0 || b < 0 || b <= a) throw new Error("مرساة مفقودة في " + htmlPath);
  const code = src.slice(a, b);
  // الأقنعة مستخرجة من المصدر نفسه لا مكتوبة يدوياً
  const defs = [/^const secOf=.*$/m, /^const dyOf=.*$/m, /^const fmt=.*$/m].map(re => {
    const m = src.match(re);
    if (!m) throw new Error("تعريف مفقود في " + htmlPath + ": " + re);
    return m[0];
  });
  const pre = defs.join("\n") + "\n";
  return new Function("DATA", pre + code + "\nreturn dyFlags;")(data);
}

function stocksOf(jsonPath) {
  const d = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
  return { DATA: d, stocks: d.stocks };
}

module.exports = { loadDyFlags, stocksOf };

/* ── أساسُ المقارنة (تصحيح ختم 05-10) ────────────────────────────────────────
   كان الأساس `git show HEAD:uat.html`. وهو يصير **مقارنةَ الملف بنفسه** لحظةَ
   إيداع التغيير، فأثبت الناقد أن عيباً مزروعاً في dyFlags ومودعاً في HEAD يُخرج
   «27 نجحت، 0 فشلت» صامتاً. فالأساس يُثبَّت على مرجع **خارج الفرع** (آخر حالٍ
   مختوم = origin/main)، ويُعلَن **لاغياً** حين لا يوجد فرق كود ليُقاس.
   وملفُ الأساس يحمل بصمة مرجعه في اسمه: اسمٌ ثابت مشترك كان يُطمَس بين حزامَين
   (test_dyflags و…_SIM كتبا كلاهما إلى uat-HEAD.html فطمس أحدهما أساس الآخر). */
/* البصمة تشمل **كل ما يُحمَّل** لا المقطعَ وحده: loadDyFlags تحقن secOf وdyOf وfmt
   وهي متغيّرات dyFlags الحرّة، فبصمةٌ على المقطع وحده تُبقي «لا فرق كود» صادقةً
   ظاهراً وكاذبةً واقعاً. مقيس في ختم 05-10ب: خلطُ Materials بـIndustrials في secOf
   رفع الوسوم 133 ⇒ 137 (أربعة أسهم تُوسَم زوراً) والحزام يُخرج ✅ وخروج 0. */
function dySlice(src) {
  const a = src.indexOf("const DY_EXTREME_PCT"), b = src.indexOf("function dyCell");
  if (a < 0 || b < 0 || b <= a) throw new Error("مرساة مفقودة");
  const free = [/^const secOf=.*$/m, /^const dyOf=.*$/m, /^const fmt=.*$/m].map(re => {
    const m = src.match(re);
    if (!m) throw new Error("تعريف حرّ مفقود: " + re);
    return m[0];
  });
  return free.join("\n") + "\n" + src.slice(a, b);
}
function loadBaseline(repoDir, ref, data, testHtml) {
  const { execSync } = require("child_process");
  const crypto = require("crypto");
  const sha = execSync(`cd ${repoDir} && git rev-parse --short ${ref}`, { encoding: "utf8" }).trim();
  const path = (process.env.TMPDIR || "/tmp") + "/_base-" + sha + "-" + process.pid + ".html";
  execSync(`cd "${repoDir}" && git show ${ref}:uat.html > "${path}"`);
  process.on("exit", () => { try { fs.unlinkSync(path); } catch (e) {} });
  const h = s => crypto.createHash("md5").update(dySlice(fs.readFileSync(s, "utf8"))).digest("hex").slice(0, 12);
  const baseHash = h(path), testHash = h(testHtml);
  return { fn: loadDyFlags(path, data), ref, sha, path, baseHash, testHash, identical: baseHash === testHash };
}
/* ── بيانات مثبتة (طلب المالك 19-10، وشروط ختمه) ────────────────────────────────
   الحزامان يتحققان من **منطق** dyFlags بأسماء أسهم بعينها («الخمسة»…)، وكانا يقرآن
   stocks-data.json **الحيّ**، فكسرهما أول جلب أسبوعي ناجح (19-10) بلا سطر كود: 24/6
   و1/6. والكسر **انتقالُ بيانات** — القوائم المالية وأساس المزوّد لا الأسعار — أعلنه
   §8-ظ سلفاً لكنه جاء بغير ما تنبّأ به (قطع 8 · تعارض 0 لا 4 · 4؛ بند مفتوح للمحلل).
   فالبيانات تُثبَّت على لقطة من تاريخ main نفسه (لا ملف ضخم مكرر): 8368b07 = تشغيلة
   19-10 اليومية، آخر لقطة قيست عليها هذه التأكيدات. ويبقى الأساس (loadBaseline) كوداً
   من origin/main على **البيانات المثبتة نفسها**، فدلتا الكود تُقاس منفصلة عن البيانات.
   وما كان يراقب **البيانات** (حضور قيم المزوّد، والجمهور الحقيقي للشاهد) يقرأ الحيّ
   عبر liveDataPath — وحارسه الحاكم في self-check-L1.py على كل تشغيلة.
   DATA_REF يتجاوز المرجع عمداً. */
const PINNED_DATA_REF = "8368b0709e17f6421577860c5697276a0073f372";
function pinnedDataPath(repoDir) {
  const { execFileSync } = require("child_process");
  const ref = process.env.DATA_REF || PINNED_DATA_REF;
  try {
    execFileSync("git", ["-C", repoDir, "cat-file", "-e", ref + "^{commit}"], { stdio: "ignore" });
  } catch (e) {
    console.error("⛔ لقطة البيانات " + ref + " غائبة عن هذه النسخة (استنساخ سطحي؟). اجلبها:\n" +
                  "   git -C " + repoDir + " fetch origin " + ref + "   (أو git fetch --deepen=500)");
    process.exit(2);
  }
  const p = (process.env.TMPDIR || "/tmp") + "/_data-" + ref.replace(/[^A-Za-z0-9]/g, "_").slice(0, 24) +
            "-" + process.pid + ".json";
  process.on("exit", () => { try { fs.unlinkSync(p); } catch (e) {} });   // يُسجَّل قبل الكتابة
  const buf = execFileSync("git", ["-C", repoDir, "show", ref + ":stocks-data.json"], { maxBuffer: 1 << 28 });
  fs.writeFileSync(p, buf);
  return { path: p, ref, label: process.env.DATA_REF ? "DATA_REF=" + ref : "لقطة مثبتة " + ref.slice(0, 7) };
}
function liveDataPath(repoDir) { return repoDir + "/stocks-data.json"; }
module.exports.liveDataPath = liveDataPath;
module.exports.pinnedDataPath = pinnedDataPath;
module.exports.PINNED_DATA_REF = PINNED_DATA_REF;
module.exports.dySlice = dySlice;
module.exports.loadBaseline = loadBaseline;
