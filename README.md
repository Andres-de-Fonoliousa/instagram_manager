# Instagram Manager

Session-based Instagram content tool for your **own account**: login/session handling, a markdown-driven posting queue, cross-posting to Telegram, and a Telegram bot for remote control. Built for the Arabic market (Damascus timezone by default) with [instagrapi](https://github.com/subzeroid/instagrapi), [aiogram](https://aiogram.dev) and [APScheduler](https://github.com/agronholm/apscheduler).

> ⚠️ **Disclaimer:** This project uses unofficial APIs. Use it only with your own account and at your own risk — automation may violate the Instagram Terms of Service and can get your account limited or banned. You have been warned.

## Features

- **Session login & 2FA** — `python main.py login` stores an instagrapi session file under `sessions/` (never committed); supports 2FA verification codes.
- **CDP session grab** — `grab2.py` pulls the `sessionid` cookie from a live Chrome DevTools instance (`chrome_debug.ps1`), so you log in with the real browser and the script harvests the session — no password handling.
- **Content queue** — posts are folders under `content/pending/<slug>/` with a `post.md` (YAML-ish frontmatter: `date`, `platforms`, per-platform captions) plus an optional image. Items move to `content/posted/` or `content/failed/` automatically.
- **Scheduled cross-posting** — `app.py` runs an APScheduler poll that publishes due items to Instagram and/or a Telegram channel, with per-platform captions.
- **Telegram control bot** — `/status`, `/queue`, `/post <slug>` from a private chat; the first `/start` pins that chat as the admin console.
- **HTML content viewer** — `make_viewer.py` renders the pending queue into `content_viewer.html` for offline review.
- **CLI utilities** — account info, followers/following export to JSON, direct photo posting.

## Project layout

```
main.py            CLI: login, info, followers, post, queue
app.py             daemon: scheduler + Telegram control bot
grab2.py           CDP-based session grab from live Chrome
grab_session.py    legacy browser-cookie session grab
adapters/          instagram / telegram posting adapters
core/              config, queue, scheduler
bot/               aiogram control router
chrome_debug.ps1   start/stop Chrome in debug mode (Windows)
cdp_close.py       gracefully close the debug Chrome via CDP
content/           pending / posted / failed post folders
sessions/          instagrapi session dumps (gitignored)
```

## Setup

Requires Python 3.12+.

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements.txt

copy config.example.json config.json   # then edit:
```

`config.json` (gitignored — real secrets live here):

```json
{
  "timezone": "Asia/Damascus",
  "poll_interval_seconds": 60,
  "default_platforms": "ig, tg",
  "instagram": { "username": "your_ig_username" },
  "telegram": { "bot_token": "123:ABC...", "channel": "@your_channel" }
}
```

### Instagram login (pick one)

1. **Password login** — `python main.py login -u your_ig_username` (prompts for password, handles 2FA).
2. **CDP grab (recommended)** — `.\chrome_debug.ps1` opens a debug Chrome, you log into Instagram normally, then `python grab2.py` harvests the session and closes the browser gracefully. Never force-kill that Chrome — it wipes the login.

### Run

```bash
python app.py          # scheduler + Telegram bot (Ctrl+C to stop)
python main.py queue path\to\post.md -i image.jpg   # add a queue item
python make_viewer.py  # regenerate content_viewer.html
```

### Telegram control

Message your bot `/start` in a private chat (this chat becomes the admin console), then use `/status`, `/queue`, `/post <slug>`.

## Post format (`content/pending/<slug>/post.md`)

```markdown
---
date: 2026-08-16 19:30
platforms: ig, tg
caption_tg: |
  Telegram-specific caption...
caption_ig: |
  Instagram caption...
---
Default caption body (used when no platform caption is set).
```

## Security notes

- `config.json` and `sessions/*` are gitignored — they hold real credentials and must never be committed.
- All account values are read from `config.json`; nothing is hardcoded.

## ملخص بالعربية

أداة لإدارة محتوى إنستغرام لحسابك الخاص تعمل بالجلسات (بدون إدخال كلمة السر يدويًا إن استخدمت الطريقة الثانية): تسجيل دخول ودعم التحقق بخطوتين، سحب الجلسة من كروم مباشرة، طابور نشر من ملفات ماركداون مع جدولة تلقائية، نشر متزامن إلى قناة تيليجرام، وبوت تيليجرام للتحكم عن بعد (`/status`، `/queue`، `/post`).

**تنبيه:** الأداة تستخدم واجهات غير رسمية — استخدمها مع حسابك الخاص فقط وتحمل المسؤولية؛ الأتمتة قد تخالف شروط استخدام إنستغرام.

## License

[MIT](LICENSE) © 2026 Andres-de-Fonoliousa
