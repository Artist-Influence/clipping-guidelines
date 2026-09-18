# Clipping Guidelines

Password-gated campaign guidelines page for clippers (currently the ENU campaign). The guidelines are plain HTML in `src/`, and `build.py` encrypts them into a single static page in `dist/` that unlocks in the browser with the team code. Nothing is served in plaintext.

## Layout

- `src/inner.html`: the guidelines content (plaintext, the file you edit)
- `src/shell.html`: the outer page with the code gate and the in-browser decrypt
- `src/line-banks.json`, `src/enu-peaks.json`: data injected into `inner.html` at build time
- `build.py`: builds `dist/index.html` (AES-GCM, key derived from the team code with PBKDF2-SHA256)
- `dist/`: what gets deployed. `dist/assets/` (audio, wordmark, icons) is the only copy of those files, so it is committed too.

## Build

Needs Python 3 and the `cryptography` package (`pip3 install cryptography`).

    python3 build.py

`dist/index.html` is rewritten with a fresh salt and IV on every build, so it changes in git even when the content does not.

For local checks only:

    python3 build.py --test

writes `dist-test/`, a copy that auto-unlocks without the code. It is gitignored and must never be deployed.

## Deploy

Vercel project `clipping-guidelines`. Deploy from inside `dist/` so the `.vercelignore` there applies:

    cd dist && vercel --prod

## Notes

- The team code is `CODE` in `build.py`. Change it there and rebuild to rotate it.
- `build.py` fails the build if any visible prose contains an em dash, en dash or double hyphen. That is on purpose, keep it.
- `dist/.vercel/` and `dist/.env.local` are local Vercel state and are gitignored. Run `vercel link` once in `dist/` on a new machine.
