#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مولّد قالب الإنتاج من صفحة التطوير — ترقية تجربة سيف (قرار المالك 04-09).

المبدأ: مصدر واحد للحقيقة. `uat.html` هي ملف التطوير الحي (تقرأ البيانات بـfetch،
‏noindex)، ويُشتق منها `template.html` آلياً بثلاث عمليات معلنة لا رابعة لها:
  1. مصدر البيانات: جسم loadData() ⇒ `return __STOCKS_DATA__;` (تضمين كالإنتاج:
     طلب واحد، يعمل بلا شبكة بعد التحميل، ولا يتأثر بـcache).
  2. إزالة وسوم التطوير: robots noindex، شارة UAT، تذييل «نسخة UAT تجريبية».
  3. إضافات الإنتاج: العنوان، رابط دقة التوصيات في الرأس، رابط النسخة الكلاسيكية،
     وعدّاد الزيارات GoatCounter (استمرارية الإحصاءات).

كل مرساة إلزامية — غيابها يُفشل التوليد بصوت عالٍ (لا قالب ناقص بصمت).

الاستخدام: python3 scripts/make-template.py [--src uat.html] [--out template.html] [--check]
"""
import argparse
import io
import os
import sys

GOATCOUNTER = ('<script data-goatcounter="https://saif-vc-sa.goatcounter.com/count" '
               'async src="//gc.zgo.at/count.js"></script>')

PROD_FOOTER = (
    'منصة سيف — تحليل منهجي للسوق السعودي. البيانات من مصادرها الرسمية وقد تتأخر أو تتعدل؛ '
    'المنهجية والدرجات معروضة كاملة داخل بطاقة كل سهم. ليست توصية استثمارية ولا نصيحة مالية.\n'
    '  · <a href="watchlist-accuracy.html">📊 دقة التوصيات</a>'
    ' · <a href="classic.html">النسخة الكلاسيكية</a>')


def swap(src, old, new, label):
    if src.count(old) != 1:
        sys.exit("⛔ مرساة مفقودة أو مكررة (%s): التوليد متوقف" % label)
    return src.replace(old, new)


def transform(s):
    # (1) مصدر البيانات — التضمين
    s = swap(s, '''async function loadData(){
  const r=await fetch("stocks-data.json",{cache:"no-cache"});
  if(!r.ok) throw new Error("HTTP "+r.status);
  return r.json();
}''', '''async function loadData(){
  /* الإنتاج: البيانات مضمّنة وقت البناء (build.py) — لا طلب شبكة ولا اعتماد على الكاش */
  return __STOCKS_DATA__;
}''', "loadData")

    # (2) إزالة وسوم التطوير
    s = swap(s, '<meta name="robots" content="noindex">\n', '', "robots")
    s = swap(s, '\n    <span class="hd-uat">UAT</span>', '', "شارة UAT")
    s = swap(s, '<title>سيف — SAIF · نسخة UAT</title>',
             '<title>سيف — SAIF | ذكاء استثماري للسوق السعودي</title>', "العنوان")
    s = swap(s, '''  نسخة UAT تجريبية لتجربة تصميم سيف الجديد — تقرأ بيانات المنصة الحقيقية نفسها ولا تُعدّل أي شيء.
  المنهجية والدرجات كما هي في النظام دون أي تغيير. ليست توصية استثمارية.
  · <a href="index.html">النسخة الحالية</a> · <a href="watchlist-accuracy.html">دقة التوصيات</a>''',
             "  " + PROD_FOOTER, "التذييل")

    # (3) إضافات الإنتاج: رابطا الدقة والكلاسيكية في الرأس + عدّاد الزيارات
    s = swap(s, '''  <div class="hd-sys">''',
             '''  <div class="hd-sys">
    <a href="watchlist-accuracy.html" class="hd-link">📊 دقة التوصيات</a>
    <a href="classic.html" class="hd-link hd-link-dim">النسخة الكلاسيكية</a>''', "روابط الرأس")
    s = swap(s, '.hd-sys{', '''.hd-link{font-size:12px; color:var(--gold); white-space:nowrap}
.hd-link:hover{color:var(--amber)}
.hd-link-dim{color:var(--text3)}
.hd-link-dim:hover{color:var(--text2)}
@media(max-width:900px){ .hd-link-dim{display:none} }
@media(max-width:640px){ .hd-link{display:none} }
.hd-sys{''', "أنماط روابط الرأس")
    s = swap(s, '</body>\n</html>', GOATCOUNTER + '\n</body>\n</html>', "GoatCounter")
    return s


def main():
    ap = argparse.ArgumentParser()
    d = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--src", default=os.path.join(d, "uat.html"))
    ap.add_argument("--out", default=os.path.join(d, "template.html"))
    ap.add_argument("--check", action="store_true",
                    help="تحقق أن القالب الحالي مطابق للمولَّد بلا كتابة")
    args = ap.parse_args()

    src = io.open(args.src, encoding="utf-8").read()
    out = transform(src)

    # حراس ما بعد التحويل — لا وسم تطوير يتسرب للإنتاج
    for bad, why in (("noindex", "وسم noindex"), ("hd-uat\">UAT", "شارة UAT"),
                     ("نسخة UAT تجريبية", "تذييل التجربة")):
        if bad in out:
            sys.exit("⛔ تسرّب وسم تطوير للقالب (%s)" % why)
    if out.count("__STOCKS_DATA__") != 1:
        sys.exit("⛔ __STOCKS_DATA__ يجب أن يظهر مرة واحدة في القالب")

    if args.check:
        cur = io.open(args.out, encoding="utf-8").read() if os.path.exists(args.out) else ""
        if cur == out:
            print("✅ القالب مطابق لمصدره (uat.html)")
            return
        sys.exit("⛔ القالب متأخر عن uat.html — أعد التوليد")

    io.open(args.out, "w", encoding="utf-8").write(out)
    print("🏗️ وُلّد %s من %s (%d بايت)" % (os.path.basename(args.out),
                                            os.path.basename(args.src), len(out)))


if __name__ == "__main__":
    main()
