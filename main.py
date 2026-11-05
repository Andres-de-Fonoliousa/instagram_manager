import argparse
import getpass
import json
import sys
from pathlib import Path

from adapters.instagram import load_client, session_path
from core.queue import DATA_DIR, enqueue


def die(msg: str):
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def cmd_login(args):
    if session_path(args.username).exists():
        print(f"Session already exists for @{args.username}.")
        print(f"Delete sessions/{args.username}.json to re-login.")
        return
    password = args.password if args.password is not None else getpass.getpass("Password: ")
    from instagrapi import Client
    from instagrapi.exceptions import TwoFactorRequired

    cl = Client(delay_range=[1, 2])
    try:
        cl.login(args.username, password)
    except TwoFactorRequired:
        code = args.code
        if not code:
            if sys.stdin.isatty():
                code = input("2FA code: ").strip()
            else:
                die("2FA required: pass --code <code> (or run in an interactive terminal)")
        if not code:
            die("2FA code is empty")
        cl.login(args.username, password, verification_code=code)
    cl.dump_settings(session_path(args.username))
    print(f"Logged in as @{args.username}. Session saved to sessions/{args.username}.json")


def cmd_info(args):
    cl = load_client(args.username)
    info = cl.account_info() if not args.target else cl.user_info(
        cl.user_id_from_username(args.target)
    )
    print(json.dumps(info.dict(), indent=2, default=str))


def cmd_relatives(args):
    cl = load_client(args.username)
    target = args.target or args.username
    user_id = cl.user_id_from_username(target)
    total = cl.user_followers_total(user_id) if not args.following else cl.user_following_total(user_id)
    print(f"Total: {total}")

    method = cl.user_following if args.following else cl.user_followers
    scraped = method(user_id, amount=args.amount)

    out = [
        {
            "username": u.username,
            "full_name": u.full_name,
            "pk": u.pk,
            "is_private": u.is_private,
            "is_verified": u.is_verified,
        }
        for u in scraped.values()
    ]
    kind = "following" if args.following else "followers"
    path = DATA_DIR / f"{target}_{kind}.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved {len(out)} {kind} -> {path}")


def cmd_post(args):
    cl = load_client(args.username)
    image = Path(args.image)
    if not image.exists():
        die(f"Image not found: {image}")
    caption = None
    if args.caption:
        caption_file = Path(args.caption)
        caption = caption_file.read_text(encoding="utf-8") if caption_file.exists() else args.caption
    media = cl.photo_upload(image, caption)
    print(f"Posted: https://www.instagram.com/p/{media.code}/")


def cmd_queue(args):
    source = Path(args.post)
    if not source.exists():
        die(f"File not found: {source}")
    image = Path(args.image) if args.image else None
    if image and not image.exists():
        die(f"Image not found: {image}")
    item = enqueue(source, image, args.name)
    print(f"Queued: {item.slug} @ {item.scheduled_at:%Y-%m-%d %H:%M}")
    print(f"  platforms: {', '.join(item.platforms) or 'none'}  image: {item.image is not None}")
    print(f"  caption preview: {item.caption[:80]!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="igbot",
        description="Instagram automation via instagrapi (session-based).",
    )
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("-u", "--username", required=True, help="Your Instagram username")

    sub = parser.add_subparsers(dest="command", required=True)

    p_login = sub.add_parser("login", parents=[parent], help="Log in and save session cookies")
    p_login.add_argument("-p", "--password", help="Password (prompted if omitted)")
    p_login.add_argument("-c", "--code", help="2FA code (only needed if Instagram requires it)")
    p_login.set_defaults(func=cmd_login)

    p_info = sub.add_parser("info", parents=[parent], help="Print account info as JSON")
    p_info.add_argument("target", nargs="?", help="Any username (defaults to your account)")
    p_info.set_defaults(func=cmd_info)

    p_followers = sub.add_parser("followers", parents=[parent], help="Scrape follower list")
    p_followers.add_argument("target", nargs="?", help="Any username (defaults to your account)")
    p_followers.add_argument("-n", "--amount", type=int, default=0, help="Max count (0 = all)")
    p_followers.set_defaults(func=cmd_relatives, following=False)

    p_following = sub.add_parser("following", parents=[parent], help="Scrape following list")
    p_following.add_argument("target", nargs="?", help="Any username (defaults to your account)")
    p_following.add_argument("-n", "--amount", type=int, default=0, help="Max count (0 = all)")
    p_following.set_defaults(func=cmd_relatives, following=True)

    p_post = sub.add_parser("post", parents=[parent], help="Post a photo")
    p_post.add_argument("image", help="Path to image file")
    p_post.add_argument("caption", nargs="?", help="Caption text or path to a caption file")
    p_post.set_defaults(func=cmd_post)

    p_queue = sub.add_parser("queue", help="Add a post to the content queue (no login needed)")
    p_queue.add_argument("post", help="Path to post.md (with --- frontmatter ---)")
    p_queue.add_argument("-i", "--image", help="Optional image file copied alongside")
    p_queue.add_argument("-n", "--name", help="Queue slug (defaults to file name)")
    p_queue.set_defaults(func=cmd_queue)

    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        die("Interrupted")


if __name__ == "__main__":
    main()