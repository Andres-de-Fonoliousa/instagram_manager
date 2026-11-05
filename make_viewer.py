"""Generate content_viewer.html from content/pending/ queue items. Stdlib only."""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.queue import scan_pending  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "content_viewer.html"

def clean(value: str) -> str:
    value = (value or "").strip()
    return "" if value in ("|", ">", ">-", "|-") else value


items = []
for it in sorted(scan_pending(), key=lambda x: x.scheduled_at):
    items.append({
        "slug": it.slug,
        "date": it.scheduled_at.strftime("%Y-%m-%d"),
        "time": it.scheduled_at.strftime("%H:%M"),
        "platforms": it.platforms,
        "has_image": it.image is not None,
        "caption_tg": clean(it.meta.get("caption_tg")) or it.caption,
        "caption_ig": clean(it.meta.get("caption_ig")) or it.caption,
        "caption": it.caption,
    })

DATA = json.dumps(items, ensure_ascii=False)

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>كوري ستور — خطة النشر</title>
<style>
  :root {
    --navy: #0A2540; --navy2: #0d2f52; --indigo: #635BFF; --lime: #81B81A;
    --text: #E8EDF5; --muted: #8fa3bd; --line: rgba(255,255,255,.08);
    --danger: #ff6b6b; --ok: #52c41a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: radial-gradient(1200px 600px at 80% -10%, var(--navy2), var(--navy));
    color: var(--text);
    font-family: "Segoe UI", Tahoma, Arial, sans-serif;
    min-height: 100vh; padding: 40px 5vw 80px;
  }
  header { max-width: 1200px; margin: 0 auto 28px; }
  .eyebrow {
    display: inline-block; color: var(--lime); font-size: 13px; font-weight: 700;
    letter-spacing: 2px; margin-bottom: 10px;
  }
  h1 { font-size: 34px; font-weight: 800; margin-bottom: 8px; }
  .sub { color: var(--muted); font-size: 15px; line-height: 1.7; }
  .stats { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 22px; }
  .stat {
    background: rgba(255,255,255,.05); border: 1px solid var(--line);
    border-radius: 14px; padding: 14px 22px; min-width: 130px;
  }
  .stat b { display: block; font-size: 26px; color: #fff; }
  .stat span { font-size: 13px; color: var(--muted); }
  .timeline {
    display: flex; gap: 10px; flex-wrap: wrap; margin: 26px 0 8px; max-width: 1200px;
  }
  .tl-chip {
    background: rgba(255,255,255,.04); border: 1px solid var(--line);
    border-radius: 999px; padding: 8px 16px; font-size: 13px; color: var(--muted);
    display: flex; align-items: center; gap: 8px;
  }
  .tl-chip .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--indigo); }
  .grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 18px; max-width: 1200px; margin: 0 auto;
  }
  .card {
    background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
    border: 1px solid var(--line); border-radius: 18px; padding: 20px;
    display: flex; flex-direction: column; gap: 12px;
    transition: transform .15s ease, border-color .15s ease;
  }
  .card:hover { transform: translateY(-3px); border-color: rgba(129,184,26,.45); }
  .card-top { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .date-badge {
    background: var(--indigo); color: #fff; border-radius: 10px;
    padding: 6px 12px; font-size: 13px; font-weight: 700; white-space: nowrap;
  }
  .chips { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip {
    font-size: 12px; font-weight: 700; border-radius: 8px; padding: 4px 10px;
    background: rgba(255,255,255,.08); color: var(--muted);
  }
  .chip.ig { background: rgba(131,58,180,.25); color: #e0aaff; }
  .chip.tg { background: rgba(38,169,224,.22); color: #8ecdf0; }
  .chip.fb { background: rgba(24,119,242,.22); color: #9cc8ff; }
  .img-status { font-size: 12px; font-weight: 700; border-radius: 8px; padding: 4px 10px; }
  .img-status.ok { background: rgba(82,196,26,.18); color: var(--ok); }
  .img-status.missing { background: rgba(255,107,107,.16); color: var(--danger); }
  .slug { font-size: 12px; color: var(--muted); font-family: Consolas, monospace; }
  .block { border-top: 1px solid var(--line); padding-top: 12px; }
  .block h4 {
    font-size: 12px; color: var(--muted); margin-bottom: 6px;
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
  }
  .cap {
    font-size: 14px; line-height: 1.9; white-space: pre-wrap; color: var(--text);
    max-height: 130px; overflow: hidden; position: relative;
  }
  .cap.open { max-height: none; }
  .cap::after {
    content: ""; position: absolute; bottom: 0; right: 0; left: 0; height: 40px;
    background: linear-gradient(transparent, rgba(13,47,82,.9)); pointer-events: none;
  }
  .cap.open::after { display: none; }
  .btn-row { display: flex; gap: 8px; }
  button {
    background: rgba(255,255,255,.07); color: var(--text); border: 1px solid var(--line);
    border-radius: 9px; padding: 7px 14px; font-size: 12.5px; font-weight: 700;
    cursor: pointer; font-family: inherit; transition: background .15s;
  }
  button:hover { background: rgba(255,255,255,.13); }
  button.copy { background: var(--lime); color: #0a2540; border: none; }
  button.copy:hover { background: #94cf2b; }
  button.toggle { background: transparent; }
  footer { text-align: center; color: var(--muted); font-size: 12.5px; margin-top: 50px; }
</style>
</head>
<body>
<header>
  <div class="eyebrow">CORESTORE · خطة النشر</div>
  <h1>منشورات المتجر والخدمات</h1>
  <p class="sub" id="sub">قائمة منشورات جاهزة للنشر على تيليجرام وإنستغرام، مع خيارات نسخ سريعة.</p>
  <div class="stats" id="stats"></div>
</header>
<div class="timeline" id="timeline"></div>
<div class="grid" id="grid"></div>
<footer>كوري ستور — بوتات، مواقع، وأنظمة للمحلات الصغيرة · @CoreStore198_bot</footer>
<script>
const ITEMS = __DATA__;
const MONTHS = ["يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"];
const PLATFORM = { ig: "IG", tg: "TG", fb: "FB" };

function fmt(d) {
  const [y, m, day] = d.split("-").map(Number);
  return `${day} ${MONTHS[m-1]} ${y}`;
}

const stats = document.getElementById("stats");
const withImg = ITEMS.filter(i => i.has_image).length;
stats.innerHTML = `
  <div class="stat"><b>${ITEMS.length}</b><span>منشور</span></div>
  <div class="stat"><b>${ITEMS.filter(i => i.platforms.includes("ig")).length}</b><span>إنستغرام</span></div>
  <div class="stat"><b>${ITEMS.filter(i => i.platforms.includes("tg")).length}</b><span>تيليجرام</span></div>
  <div class="stat"><b>${withImg}</b><span>بصورة</span></div>
  <div class="stat"><b>${ITEMS.length - withImg}</b><span>بانتظار الصورة</span></div>`;

const tl = document.getElementById("timeline");
tl.innerHTML = ITEMS.map(i => `
  <div class="tl-chip"><span class="dot"></span>${fmt(i.date)} · ${i.time}</div>`).join("");

const grid = document.getElementById("grid");
grid.innerHTML = ITEMS.map(i => {
  const img = i.has_image
    ? `<span class="img-status ok">بصورة ✓</span>`
    : `<span class="img-status missing">بانتظار صورة</span>`;
  const chips = i.platforms.map(p => `<span class="chip ${p}">${PLATFORM[p] || p}</span>`).join("");
  return `
  <div class="card">
    <div class="card-top">
      <span class="date-badge">${fmt(i.date)} · ${i.time}</span>
      <div class="chips">${chips}${img}</div>
    </div>
    <div class="slug">${i.slug}</div>
    <div class="block">
      <h4>تيليجرام</h4>
      <div class="cap" data-full="${encodeURIComponent(i.caption_tg)}"></div>
      <div class="btn-row">
        <button class="copy" onclick="copyText(this, '${encodeURIComponent(i.caption_tg)}')">نسخ</button>
        <button class="toggle" onclick="toggleCap(this)">عرض كامل</button>
      </div>
    </div>
    <div class="block">
      <h4>إنستغرام</h4>
      <div class="cap" data-full="${encodeURIComponent(i.caption_ig)}"></div>
      <div class="btn-row">
        <button class="copy" onclick="copyText(this, '${encodeURIComponent(i.caption_ig)}')">نسخ</button>
        <button class="toggle" onclick="toggleCap(this)">عرض كامل</button>
      </div>
    </div>
  </div>`;
}).join("");

document.querySelectorAll(".cap").forEach(el => {
  el.textContent = decodeURIComponent(el.dataset.full);
});

function copyText(btn, text) {
  navigator.clipboard.writeText(decodeURIComponent(text)).then(() => {
    const old = btn.textContent; btn.textContent = "تم النسخ ✓";
    setTimeout(() => { btn.textContent = old; }, 1200);
  });
}
function toggleCap(btn) {
  const cap = btn.closest(".block").querySelector(".cap");
  cap.classList.toggle("open");
  btn.textContent = cap.classList.contains("open") ? "طيّ" : "عرض كامل";
}
</script>
</body>
</html>"""

OUT.write_text(HTML.replace("__DATA__", DATA), encoding="utf-8")
print(f"viewer written: {OUT}")
print(f"posts embedded: {len(items)}")
