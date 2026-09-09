#!/bin/zsh
# Publish the OneBrowse website to GitHub Pages and put its URLs on App Store Connect.
#
#     gh auth login              # once; already done on this Mac
#     marketing/site/deploy.sh   # then this, as often as the site changes
#
# Creates the public repository the first time (default name: onebrowse), rebuilds the
# pages with the repository's issue tracker as the public support channel, commits and
# pushes, turns on GitHub Pages from docs/ on main, waits for the site to answer, and
# writes the support, marketing and privacy-policy URLs into marketing/listing.json and
# up to App Store Connect.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(cd ../.. && pwd)
NAME=${1:-onebrowse}

gh auth status >/dev/null 2>&1 || { echo "Not signed in. Run: gh auth login"; exit 1; }
OWNER=$(gh api user --jq .login)
REPO="$OWNER/$NAME"
WEB_URL="https://github.com/$REPO"

# 1. The pages, with the tracker as the public support channel.
python3 build_site.py --issues-url "$WEB_URL/issues"

# 2. A repository, created once, and the commit.
[ -d .git ] || git init -q -b main
git add -A
if ! git diff --cached --quiet; then
  git commit -q -m "Site: $(date '+%Y-%m-%d %H:%M')"
fi
if gh repo view "$REPO" >/dev/null 2>&1; then
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "$WEB_URL.git"
  git push -q -u origin main
else
  echo "creating $WEB_URL"
  gh repo create "$NAME" --public --source . --remote origin --push \
    --description "OneBrowse website: support, privacy policy and terms." >/dev/null
fi
echo "pushed to $WEB_URL"

# 3. GitHub Pages from docs/ on main.
if gh api "repos/$REPO/pages" >/dev/null 2>&1; then
  gh api -X PUT "repos/$REPO/pages" --input - >/dev/null <<'JSON'
{"source":{"branch":"main","path":"/docs"}}
JSON
else
  gh api -X POST "repos/$REPO/pages" --input - >/dev/null <<'JSON'
{"source":{"branch":"main","path":"/docs"}}
JSON
fi
PAGES_URL=$(gh api "repos/$REPO/pages" --jq .html_url)
PAGES_URL=${PAGES_URL%/}
echo "pages: $PAGES_URL"

# 4. Proof the pages answer. The first build takes a minute or two.
CODE=000
for i in {1..40}; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "$PAGES_URL/privacy.html" || true)
  [ "$CODE" = 200 ] && break
  printf '  waiting for the site (%s)\r' "$CODE"
  sleep 10
done
echo
[ "$CODE" = 200 ] || { echo "the site is not answering yet ($CODE); check $WEB_URL/settings/pages"; exit 1; }
echo "site: $PAGES_URL (privacy.html answered 200)"

# 5. Onto the App Store listing.
python3 - "$ROOT/marketing/listing.json" "$PAGES_URL" <<'PY'
import json, sys
path, url = sys.argv[1], sys.argv[2]
d = json.load(open(path))
d["supportUrl"] = f"{url}/support.html"
d["marketingUrl"] = f"{url}/"
d["privacyPolicyUrl"] = f"{url}/privacy.html"
with open(path, "w") as handle:
    json.dump(d, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
print("listing.json: support, marketing and privacy URLs set")
PY
python3 "$ROOT/scripts/listing.py" --copy "$ROOT/marketing/listing.json"
