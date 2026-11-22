"""Turn a "Submit a claim" issue into a tracker entry.

  python scripts/claim_bot.py check  <event.json>   validate a submission, write comment.md
  python scripts/claim_bot.py add    <event.json>   add an approved submission to data/claims.json
  python scripts/claim_bot.py images                fetch missing card images for every claim

The issue body is untrusted input: it is only parsed as text, never executed.
The verdict status comes from the maintainer's label (confirmed, partly-true, ...), not the submitter.
"""
import html
import io
import ipaddress
import json
import re
import socket
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "claims.json"
IMG = ROOT / "img"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
FIELDS = {
    "The claim": "claim", "Who made it": "who", "When (year and month)": "date",
    "Link to the claim": "claim_url", "What the evidence shows": "verdict",
    "Evidence link": "evidence_url", "Second evidence link (optional)": "evidence2_url",
    "Suggested verdict": "suggested",
}
SUGGESTED = {"Confirmed": "confirmed", "Partly true": "partly", "Unverified": "unverified",
             "Disputed": "disputed", "Walked back": "walked-back", "False": "false"}
LABEL_STATUS = {"confirmed": "confirmed", "partly-true": "partly", "unverified": "unverified",
                "disputed": "disputed", "walked-back": "walked-back", "false": "false"}
LIMITS = {"claim": 90, "who": 60, "verdict": 140}
REQUIRED = ["claim", "who", "date", "claim_url", "verdict", "evidence_url"]


def parse(body):
    out = {}
    for block in re.split(r"^### ", body or "", flags=re.M)[1:]:
        label, _, value = block.partition("\n")
        value = value.strip()
        key = FIELDS.get(label.strip())
        if key and value and value != "_No response_":
            out[key] = re.sub(r"\s+", " ", value)
    return out


def public_http_url(url):
    try:
        u = urllib.parse.urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            return False
        for info in socket.getaddrinfo(u.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        return True
    except Exception:
        return False


def fetch(url, limit):
    if not public_http_url(url):
        raise ValueError("not a public http(s) link")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.geturl(), r.read(limit)


def og_image(page, base):
    for tag in re.findall(r"<meta[^>]+>", page, re.I):
        if re.search(r'(property|name)\s*=\s*["\']?(og:image(:secure_url)?|twitter:image(:src)?)(["\'\s>]|$)', tag, re.I):
            m = re.search(r'content\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s>]+))', tag, re.I)
            if m:
                return urllib.parse.urljoin(base, html.unescape(next(g for g in m.groups() if g)))
    return None


def host(url):
    return urllib.parse.urlparse(url).netloc.removeprefix("www.")


def save_image(page_url, cid):
    """Fetch the page's preview image into img/<cid>.jpg. Returns the fields to merge, or {}."""
    from PIL import Image
    final, page = fetch(page_url, 2_500_000)
    img_url = og_image(page.decode("utf-8", "replace"), final)
    if not img_url:
        return {}
    if img_url.startswith("http://"):
        img_url = "https://" + img_url[7:]
    _, data = fetch(img_url, 8_000_000)
    im = Image.open(io.BytesIO(data)).convert("RGB")
    ratio = im.width / max(im.height, 1)
    im.thumbnail((900, 900))
    IMG.mkdir(exist_ok=True)
    im.save(IMG / f"{cid}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
    out = {"image": f"img/{cid}.jpg", "imageCredit": host(page_url), "imagePage": page_url}
    if not 1.6 <= ratio <= 2.2:
        out["imageFit"] = "contain"
    return out


def validate(e):
    problems = [f"**{k}** is missing" for k in REQUIRED if not e.get(k)]
    if e.get("date") and not re.fullmatch(r"(19|20)\d\d-(0[1-9]|1[0-2])", e["date"]):
        problems.append("**When** should look like `2026-07`")
    for k, n in LIMITS.items():
        if len(e.get(k, "")) > n:
            problems.append(f"**{k}** is too long ({len(e[k])} characters, max {n})")
    for k in ("claim_url", "evidence_url", "evidence2_url"):
        if e.get(k) and not public_http_url(e[k]):
            problems.append(f"**{k}** must be a public http(s) link")
    return problems


def write_comment(text):
    Path("comment.md").write_text(text + "\n", encoding="utf-8")


def check(event):
    e = parse(event["issue"].get("body", ""))
    problems = validate(e)
    reach = []
    for k in ("claim_url", "evidence_url", "evidence2_url"):
        if e.get(k) and public_http_url(e[k]):
            try:
                fetch(e[k], 200_000)
                reach.append(f"- {host(e[k])}: opens")
            except Exception as ex:
                reach.append(f"- {host(e[k])}: could not open it ({type(ex).__name__})")
    lines = ["Thanks for submitting a claim!", ""]
    if problems:
        lines += ["Please edit the issue to fix these:", *[f"- {p}" for p in problems], ""]
    else:
        lines += ["The form looks complete. A maintainer will read the evidence, add a verdict label "
                  "(`confirmed`, `partly-true`, `unverified`, `disputed`, `walked-back` or `false`) and `approved`. "
                  "The site updates automatically after that.", ""]
    if reach:
        lines += ["Link check:", *reach]
    write_comment("\n".join(lines))
    return 0


def add(event):
    issue = event["issue"]
    e = parse(issue.get("body", ""))
    problems = validate(e)
    labels = {l["name"] for l in issue.get("labels", [])}
    status = next((LABEL_STATUS[l] for l in LABEL_STATUS if l in labels), None)
    if not status:
        problems.append("add a verdict label (`confirmed`, `partly-true`, `unverified`, `disputed`, `walked-back` or `false`) before `approved`")
    if problems:
        write_comment("Could not add this claim:\n" + "\n".join(f"- {p}" for p in problems))
        return 1
    claims = json.loads(DATA.read_text(encoding="utf-8"))
    cid = f"i{issue['number']}"
    if any(x.get("id") == cid for x in claims):
        write_comment("This claim is already on the site.")
        return 0
    entry = {
        "id": cid, "date": e["date"], "claim": e["claim"].strip("\"“”"), "who": e["who"], "status": status,
        "verdict": e["verdict"], "detail": e["verdict"],
        "sources": [{"label": host(e[k]), "url": e[k]} for k in ("claim_url", "evidence_url", "evidence2_url") if e.get(k)],
        "issue": issue["html_url"],
    }
    for page in (e["claim_url"], e["evidence_url"]):
        try:
            got = save_image(page, cid)
            if got:
                entry.update(got)
                break
        except Exception as ex:
            print("image skipped:", page, type(ex).__name__, ex)
    claims.append(entry)
    DATA.write_text(json.dumps(claims, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    write_comment("Added to the AI Claim Tracker. It will be live at https://woletee.github.io/ai-claims-tracker/ in a minute or two. Thanks!")
    print("added", cid, entry["claim"])
    return 0


def images():
    claims = json.loads(DATA.read_text(encoding="utf-8"))
    for x in claims:
        if x.get("image") and (ROOT / x["image"]).exists():
            continue
        pages = [x.get("imagePage")] + [s["url"] for s in x.get("sources", [])]
        for page in [p for p in pages if p]:
            try:
                got = save_image(page, x["id"])
                if got:
                    x.update(got)
                    print(x["id"], "ok", page)
                    break
            except Exception as ex:
                print(x["id"], "skip", page, type(ex).__name__)
        else:
            print(x["id"], "NO IMAGE")
    DATA.write_text(json.dumps(claims, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    mode = sys.argv[1]
    if mode == "images":
        sys.exit(images())
    event = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    sys.exit({"check": check, "add": add}[mode](event))
