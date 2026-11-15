#!/usr/bin/env python3
"""Verschluesselt die Dashboard-Daten fuer die oeffentliche Seite.
Aufruf: python3 encrypt.py <ZUGANGSCODE> <daten.json> <ziel/daten.enc.json> [alt/daten.enc.json]
Mit der alten Datei werden Bereiche (z. B. "verdienst"), die in daten.json fehlen, aus dem bisherigen Stand übernommen.
daten.json = {"bestand": {...}, "tagebuch": [...], "buch": {...}} (gleiches Format wie die Claude-Artifact-Datenbank).
Benoetigt: pip install cryptography. Der Zugangscode gehoert NICHT in dieses Repository."""
import sys, os, json, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 600000

def main():
    pin, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    data = json.load(open(src, encoding="utf-8"))
    if len(sys.argv) > 4 and os.path.exists(sys.argv[4]):
        old = json.load(open(sys.argv[4]))
        ok = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=base64.b64decode(old["salt"]), iterations=old["iter"]).derive(pin.encode())
        prev = json.loads(AESGCM(ok).decrypt(base64.b64decode(old["iv"]), base64.b64decode(old["ct"]), None))
        for k, v in prev.items():
            if k not in data: data[k] = v
    for k in ("bestand", "tagebuch"):
        assert k in data, "fehlt: " + k
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pin.encode())
    ct = AESGCM(key).encrypt(iv, json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode(), None)
    b = lambda x: base64.b64encode(x).decode()
    json.dump(dict(v=1, iter=ITER, salt=b(salt), iv=b(iv), ct=b(ct)), open(dst, "w"))
    # Selbsttest: wieder entschluesseln
    box = json.load(open(dst))
    k2 = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=base64.b64decode(box["salt"]), iterations=ITER).derive(pin.encode())
    assert json.loads(AESGCM(k2).decrypt(base64.b64decode(box["iv"]), base64.b64decode(box["ct"]), None)) == data
    print("ok", len(data["tagebuch"]), "Eintraege,", len(data["bestand"].get("zeilen", [])), "Faecher")

if __name__ == "__main__":
    main()
