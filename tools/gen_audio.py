"""Vyrobí nahrávky všech hlášek hry hlasem Microsoft Antonín (edge-tts).

texts.json  – seznam textů (vytváří hra funkcí __allTexts)
audio/      – MP3 soubory + index.json (text -> soubor), hra je přehrává místo syntézy řeči
Už existující nahrávky se přeskočí, nepoužívané se smažou.
"""
import asyncio, hashlib, json, os, sys

import edge_tts

VOICE = os.environ.get("VOICE", "cs-CZ-AntoninNeural")
OUT = "audio"
texts = json.load(open("texts.json", encoding="utf-8"))
os.makedirs(OUT, exist_ok=True)
idx, failed = {}, []
sem = asyncio.Semaphore(int(os.environ.get("PARALLEL", "6")))


def fname(t: str) -> str:
    return hashlib.sha1((VOICE + "|" + t).encode("utf-8")).hexdigest()[:16] + ".mp3"


async def one(t: str) -> None:
    fn = fname(t)
    path = os.path.join(OUT, fn)
    if not (os.path.exists(path) and os.path.getsize(path) > 400):
        async with sem:
            for attempt in range(5):
                try:
                    await edge_tts.Communicate(t, VOICE).save(path)
                    if os.path.getsize(path) > 400:
                        break
                except Exception as e:  # síť / omezení služby – zkusit znovu
                    print("retry", attempt + 1, repr(t), e, file=sys.stderr)
                await asyncio.sleep(2 * (attempt + 1))
    if os.path.exists(path) and os.path.getsize(path) > 400:
        idx[t] = fn
    else:
        failed.append(t)


async def main() -> None:
    await asyncio.gather(*(one(t) for t in texts))
    keep = set(idx.values())
    for f in os.listdir(OUT):
        if f.endswith(".mp3") and f not in keep:
            os.remove(os.path.join(OUT, f))
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(idx, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"hotovo {len(idx)}/{len(texts)} nahrávek, chybí {len(failed)}")
    for t in failed[:30]:
        print("  chybí:", t)


asyncio.run(main())
