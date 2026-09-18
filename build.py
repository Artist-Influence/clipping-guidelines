#!/usr/bin/env python3
"""Build the campaign guidelines reference:: encrypt src/inner.html (AES-GCM, PBKDF2-SHA256) into src/shell.html.

    python3 build.py            # production build
    python3 build.py --test     # also writes dist-test/ that auto-unlocks (local checks only, never deploy)
"""
import base64, json, re, secrets, sys, shutil, html as htmllib
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = Path(__file__).resolve().parent
CODE = "arty"
ITER = 250_000
b64 = lambda b: base64.b64encode(b).decode()

inner = (ROOT / "src/inner.html").read_text(encoding="utf-8")
peaks = (ROOT / "src/enu-peaks.json").read_text(encoding="utf-8").strip()
assert inner.count("__PEAKS_ENU__") == 1
inner = inner.replace("__PEAKS_ENU__", peaks)
banks = (ROOT / "src/line-banks.json").read_text(encoding="utf-8").strip()
assert inner.count("__LINE_BANKS__") == 1
inner = inner.replace("__LINE_BANKS__", banks)
shell = (ROOT / "src/shell.html").read_text(encoding="utf-8")
assert shell.count("__PAYLOAD__") == 1

# prose check: no em dashes, en dashes or double hyphens in anything a person reads
visible = re.sub(r"<!--.*?-->", " ", inner, flags=re.S)
visible = re.sub(r"<[^>]+>", " ", visible)
visible = htmllib.unescape(visible)
bad = [m.group(0) for m in re.finditer(r".{0,40}(—|–|--).{0,40}", visible)]
gate_text = re.sub(r"<[^>]+>", " ", shell[shell.index("<body>"):shell.index("<script>")])
bad += [m.group(0) for m in re.finditer(r".{0,40}(—|–|--).{0,40}", gate_text)]
if bad:
    print("DASH CHECK FAILED:"); [print("  ", b) for b in bad]; sys.exit(1)

salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(CODE.encode())
ct = AESGCM(key).encrypt(iv, inner.encode("utf-8"), None)
payload = {"v": 1, "salt": b64(salt), "iv": b64(iv), "iter": ITER, "ct": b64(ct)}
out = shell.replace("__PAYLOAD__", json.dumps(payload))

# round trip
assert AESGCM(key).decrypt(iv, ct, None).decode("utf-8") == inner
for marker in ("What worked on house campaigns", "Claim before you use", "The exact moments", "STRIKES (they count for 90 days)"):
    assert marker in inner and marker not in out, f"plaintext leaked or marker missing: {marker}"

dist = ROOT / "dist"
(dist / "index.html").write_text(out, encoding="utf-8")
(dist / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
(dist / "vercel.json").write_text(json.dumps({
    "headers": [
        {"source": "/(.*)", "headers": [
            {"key": "X-Robots-Tag", "value": "noindex, nofollow"},
            {"key": "X-Content-Type-Options", "value": "nosniff"},
            {"key": "Referrer-Policy", "value": "same-origin"}
        ]}
    ]
}, indent=2) + "\n")
(dist / ".vercelignore").write_text("*\n!index.html\n!vercel.json\n!robots.txt\n!assets\n!assets/**\n")
print(f"built dist/index.html  {len(out.encode())/1024:.0f} KB  (inner {len(inner.encode())/1024:.0f} KB, encrypted)")

if "--test" in sys.argv:
    test = ROOT / "dist-test"
    if test.exists():
        shutil.rmtree(test)
    shutil.copytree(dist, test, ignore=shutil.ignore_patterns(".vercel", ".env*", ".vercelignore"))
    marker = "const saved = store.get('sfc-code');"
    assert out.count(marker) == 1, "test build: auto-unlock marker not found"
    t = out.replace(marker, "const saved = 'arty';")
    (test / "index.html").write_text(t, encoding="utf-8")
    print("built dist-test/ (auto-unlock, local only)")
