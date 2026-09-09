#!/usr/bin/env python3
"""Build the OneBrowse website into marketing/site/docs/.

    python3 marketing/site/build_site.py [--issues-url URL] [--app-store-url URL]

Four static pages and nothing else: a landing page built from the App Store frames, the
Privacy Policy and Terms lifted straight out of LegalView.swift so the site can never
drift from what the app shows, and a support page. Hosted on GitHub Pages from the docs/
folder of the main branch; see deploy.sh.
"""
import argparse
import html
import os
import re
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(HERE, "docs")
LEGAL = os.path.join(ROOT, "OneBrowse/Views/LegalView.swift")
FRAMES = os.path.join(ROOT, "marketing/appstore/iphone-6.9")
ICON = os.path.join(ROOT, "OneBrowse/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png")


# MARK: - The legal text, from the app

def legal_sections(name):
    """The (heading, body) pairs of `static let <name>` in LegalView.swift."""
    with open(LEGAL) as handle:
        source = handle.read()
    contact = re.search(r'private static let contact = "([^"]+)"', source).group(1)
    updated = re.search(r'static let lastUpdated = "([^"]+)"', source).group(1)
    start = source.index(f"static let {name}: [(heading: String, body: String)] = [")
    end = source.index("\n    ]", start)
    block = source[start:end]
    pairs = re.findall(r'\("((?:[^"\\]|\\.)*)",\s*"((?:[^"\\]|\\.)*)"\)', block)

    def unescape(text):
        text = text.replace('\\"', '"').replace("\\n", "\n")
        text = text.replace("\\u{201C}", "“").replace("\\u{201D}", "”")
        text = text.replace("\\(contact)", contact)
        return text

    return updated, contact, [(unescape(h), unescape(b)) for h, b in pairs]


def body_html(body):
    out, items = [], []
    for line in body.split("\n"):
        if line.startswith("• "):
            items.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if items:
            out.append("<ul>" + "".join(items) + "</ul>")
            items = []
        if line.strip():
            text = html.escape(line)
            text = re.sub(r"([\w.+-]+@[\w-]+\.[\w.-]+)", r'<a href="mailto:\1">\1</a>', text)
            out.append(f"<p>{text}</p>")
    if items:
        out.append("<ul>" + "".join(items) + "</ul>")
    return "\n".join(out)


def legal_page(name, title):
    updated, _, sections = legal_sections(name)
    parts = [f'<p class="meta">Last updated {html.escape(updated)}</p>']
    for heading, body in sections:
        if heading:
            parts.append(f"<h2>{html.escape(heading)}</h2>")
        parts.append(body_html(body))
    return title, "\n".join(parts)


# MARK: - Pages

STYLE = """
:root { --blue: #2A3EAE; --ink: #0A0E24; --orange: #FFB35C; --text: #1b1f33; --muted: #5b6075; --line: #e6e8f0; }
* { box-sizing: border-box; }
html { color-scheme: light; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: var(--text); background: #fff; -webkit-font-smoothing: antialiased; line-height: 1.55; }
a { color: var(--blue); }
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 24px; }
header.top { position: sticky; top: 0; z-index: 5; background: rgba(255,255,255,.86); backdrop-filter: saturate(180%) blur(14px); border-bottom: 1px solid var(--line); }
header.top .wrap { display: flex; align-items: center; justify-content: space-between; height: 60px; }
.brand { display: flex; align-items: center; gap: 10px; font-weight: 700; text-decoration: none; color: var(--text); }
.brand img { width: 28px; height: 28px; border-radius: 7px; }
nav a { margin-left: 22px; text-decoration: none; color: var(--muted); font-weight: 500; }
nav a:hover { color: var(--text); }
.hero { background: radial-gradient(70% 45% at 50% -5%, rgba(120,150,255,.55), rgba(120,150,255,0) 70%), linear-gradient(180deg, var(--blue) 0%, #1B2A7A 45%, var(--ink) 100%); color: #fff; padding: 84px 0 0; text-align: center; overflow: hidden; }
.hero h1 { font-size: clamp(40px, 7vw, 76px); line-height: 1.02; letter-spacing: -.028em; margin: 0 auto 18px; max-width: 14ch; font-weight: 800; }
.hero h1 span { color: var(--orange); white-space: nowrap; }
.hero p.lead { font-size: clamp(17px, 2.2vw, 22px); color: rgba(255,255,255,.78); max-width: 620px; margin: 0 auto 30px; }
.pill { display: inline-block; padding: 9px 18px; border-radius: 999px; background: rgba(255,255,255,.14); border: 1.5px solid rgba(255,255,255,.28); font-weight: 700; font-size: 15px; margin-bottom: 22px; }
.cta { display: inline-flex; align-items: center; gap: 10px; background: #fff; color: var(--ink); text-decoration: none; font-weight: 700; padding: 14px 24px; border-radius: 999px; font-size: 17px; }
.cta:hover { background: #f1f3ff; }
.gallery { display: flex; padding: 64px 0 0; overflow-x: auto; scroll-snap-type: x mandatory; scrollbar-width: none; }
.gallery::-webkit-scrollbar { display: none; }
/* Centred when it fits, scrollable from the first picture when it does not. */
.gallery-inner { display: flex; gap: 22px; margin: 0 auto; padding: 0 24px; }
.gallery img { width: 300px; height: auto; border-radius: 34px; box-shadow: 0 30px 60px rgba(0,0,0,.45); scroll-snap-align: center; flex: 0 0 auto; transform: translateY(24px); }
section.features { padding: 72px 0 24px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 28px; }
.card h3 { margin: 0 0 8px; font-size: 20px; letter-spacing: -.01em; }
.card p { margin: 0; color: var(--muted); }
section.free { background: #f6f7fb; padding: 56px 0; margin-top: 48px; }
section.free h2, section.features h2, main.doc h1 { font-size: clamp(28px, 4vw, 40px); letter-spacing: -.02em; line-height: 1.1; margin: 0 0 14px; }
main.doc { padding: 56px 0 72px; }
main.doc .wrap { max-width: 760px; }
main.doc h2 { font-size: 22px; margin: 34px 0 8px; letter-spacing: -.01em; }
main.doc p, main.doc li { color: #2e3348; font-size: 17px; }
main.doc .meta { color: var(--muted); font-size: 14px; }
footer { border-top: 1px solid var(--line); padding: 28px 0 44px; color: var(--muted); font-size: 14px; }
footer .wrap { display: flex; flex-wrap: wrap; gap: 14px 26px; justify-content: space-between; align-items: center; }
footer a { color: var(--muted); text-decoration: none; margin-right: 18px; }
footer a:hover { color: var(--text); }
.faq details { border-top: 1px solid var(--line); padding: 14px 0; }
.faq details:last-child { border-bottom: 1px solid var(--line); }
.faq summary { font-weight: 600; cursor: pointer; font-size: 17px; }
.faq p { margin: 10px 0 0; }
@media (max-width: 640px) { nav a { margin-left: 14px; font-size: 14px; } .gallery img { width: 240px; border-radius: 28px; } }
"""


def shell(title, body, description, path_prefix=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="icon" href="img/icon.png">
<link rel="apple-touch-icon" href="img/icon.png">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="index.html"><img src="img/icon.png" alt="">OneBrowse</a>
  <nav><a href="support.html">Support</a><a href="privacy.html">Privacy</a><a href="terms.html">Terms</a></nav>
</div></header>
{body}
<footer><div class="wrap">
  <div>© 2026 Michael Berinshteyn and Bryson · OneBrowse is free, with no ads and no subscriptions.</div>
  <div><a href="support.html">Support</a><a href="privacy.html">Privacy Policy</a><a href="terms.html">Terms of Service</a></div>
</div></footer>
</body></html>
"""


def landing(app_store_url):
    frames = "".join(f'<img src="img/frame-0{i}.png" alt="OneBrowse screenshot {i}" loading="lazy">' for i in range(1, 7))
    body = f"""
<section class="hero"><div class="wrap">
  <div class="pill">Free · No ads · No subscriptions</div>
  <h1>Your sites. <span>Zero pop&#8209;ups.</span></h1>
  <p class="lead">OneBrowse is a browser for the one or two sites you actually use: the streaming, sports and recipe sites that fight you on a phone. Pin a site, tap its button, and everything it throws at you — pop-ups, redirects, overlays, cookie walls — is stopped before you see it.</p>
  <a class="cta" href="{html.escape(app_store_url)}">Download on the App Store</a>
  <div class="gallery"><div class="gallery-inner">{frames}</div></div>
</div></section>

<section class="features"><div class="wrap">
  <h2>What it does</h2>
  <div class="grid">
    <div class="card"><h3>Stops it before it loads</h3><p>Pop-up windows are refused inside the page before the site's own code runs. Overlays are cleared, scrolling is unlocked, and redirects off your site are dropped without asking.</p></div>
    <div class="card"><h3>Three levels, per site</h3><p>Standard stops pop-ups and leaves the page alone. Strict also removes the boxes that cover a page. Nuclear strips bars, chat bubbles and anything pinned over the content.</p></div>
    <div class="card"><h3>See what it stopped</h3><p>What Was Blocked shows every site, every day, by kind: pop-ups, redirects, overlays, nags, cookie banners answered and tracking links cleaned.</p></div>
    <div class="card"><h3>Browse anything</h3><p>Free Browse gives you tabs, private tabs, reader view, downloads and a desktop-site switch, with the same blocking on every page. Make any page an app with one tap.</p></div>
    <div class="card"><h3>On iPhone and iPad</h3><p>Sign in with Apple if you want your pinned sites, favourites and settings to follow you over iCloud. No account is needed to use the app. A Mac version is on its way.</p></div>
    <div class="card"><h3>Real AirPlay</h3><p>A site's video goes to your TV as a stream, not as screen mirroring, so the phone stays free and the picture stays full resolution.</p></div>
  </div>
</div></section>

<section class="free"><div class="wrap">
  <h2>Free means free</h2>
  <p>No ads, no subscriptions, no in-app purchases, and no server: there is nowhere for your data to go. Read the <a href="privacy.html">Privacy Policy</a> — it is short.</p>
</div></section>
"""
    return shell("OneBrowse — your sites, without pop-ups", body,
                 "A free browser for the sites you actually use. Pop-ups, redirects and overlays stopped before you see them. No ads, no subscriptions.")


def support(contact, issues_url, app_store_url):
    issues = f'<p>Prefer to write it down in public? <a href="{html.escape(issues_url)}">Open an issue</a> on the project’s tracker.</p>' if issues_url else ""
    body = f"""
<main class="doc"><div class="wrap">
  <h1>Support</h1>
  <p>OneBrowse is made by two people, and we read everything that comes in.</p>

  <h2>Report a site from inside the app</h2>
  <p>Open the site, tap the shield, then <strong>Report</strong>. That builds a short diagnostic (the site, the blocking level, and the last few things the app did on that page) and hands it to the share sheet so you can send it to us. Nothing is sent on its own.</p>

  <h2>Email</h2>
  <p><a href="mailto:{contact}">{contact}</a></p>
  {issues}

  <h2>Common questions</h2>
  <div class="faq">
    <details><summary>A site does not work properly with OneBrowse.</summary><p>Open the site, tap the shield and choose <strong>Pause on This Site</strong>. That site then gets an ordinary browser while everything else stays protected. If you can spare a minute, tap <strong>Report</strong> so we can fix it for everyone.</p></details>
    <details><summary>A link on my pinned site does nothing.</summary><p>Site Lock keeps a pinned site on its own domain, so links and redirects to other sites are dropped without asking. Turn Site Lock off from the shield to follow a link elsewhere, or open the link in Free Browse.</p></details>
    <details><summary>AirPlay sends only the sound to my TV.</summary><p>Use the AirPlay button inside OneBrowse (on iPhone it is in the Page menu, the circle with three dots) rather than Control Center. Control Center moves only the audio; the button inside the app moves the video. Some sites build the video inside the page in a way AirPlay cannot carry; for those, Screen Mirroring is the option.</p></details>
    <details><summary>Where is my name from Sign in with Apple?</summary><p>Apple shares your name only on the very first sign-in. OneBrowse keeps it for you so it survives a reinstall. If you signed in with an early build, revoke OneBrowse under Settings → Apple Account → Sign in with Apple, then sign in again.</p></details>
    <details><summary>Why is the app rated 17+?</summary><p>Every web browser that can reach the open web carries that rating on the App Store. OneBrowse itself shows nothing of its own.</p></details>
    <details><summary>Is it really free?</summary><p>Yes. No ads, no subscriptions, no in-app purchases. <a href="{html.escape(app_store_url)}">Download it on the App Store</a>.</p></details>
  </div>
</div></main>
"""
    return shell("OneBrowse Support", body, "Get help with OneBrowse: report a site from inside the app, or email us.")


def doc_page(title, inner):
    return shell(f"OneBrowse {title}", f'<main class="doc"><div class="wrap"><h1>{html.escape(title)}</h1>\n{inner}\n</div></main>',
                 f"OneBrowse {title}.")


def resize(src, dst, width):
    subprocess.run(["sips", "-Z", str(width), src, "--out", dst], check=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issues-url", default="")
    parser.add_argument("--app-store-url", default="https://apps.apple.com/app/id6808476200")
    args = parser.parse_args()

    shutil.rmtree(PUBLIC, ignore_errors=True)
    os.makedirs(os.path.join(PUBLIC, "img"))
    resize(ICON, os.path.join(PUBLIC, "img/icon.png"), 256)
    for i in range(1, 7):
        name = sorted(f for f in os.listdir(FRAMES) if f.startswith(f"0{i}-"))[0]
        resize(os.path.join(FRAMES, name), os.path.join(PUBLIC, f"img/frame-0{i}.png"), 720)

    _, contact, _ = legal_sections("privacy")
    pages = {
        "index.html": landing(args.app_store_url),
        "support.html": support(contact, args.issues_url, args.app_store_url),
        "privacy.html": doc_page(*legal_page("privacy", "Privacy Policy")),
        "terms.html": doc_page(*legal_page("terms", "Terms of Service")),
    }
    for name, content in pages.items():
        with open(os.path.join(PUBLIC, name), "w") as handle:
            handle.write(content)
    with open(os.path.join(PUBLIC, "style.css"), "w") as handle:
        handle.write(STYLE.strip() + "\n")
    # Plain files, served as they are: no Jekyll pass.
    open(os.path.join(PUBLIC, ".nojekyll"), "w").close()
    print(f"built {len(pages)} pages into {PUBLIC}")


if __name__ == "__main__":
    main()
