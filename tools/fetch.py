"""Downloads from wago.tools, cached on disk. wago answers 502/504 under load, so retry."""
import csv
import io
import os
import time
import urllib.error
import urllib.request

CASC = "https://wago.tools/api/casc/{}"
DB2 = "https://wago.tools/db2/{}/csv"
LISTFILE = "https://github.com/wowdev/wow-listfile/releases/latest/download/community-listfile.csv"
UA = {"User-Agent": "mod-retail-druid-forms/1.0"}


def fetch(url, path, tries=6):
    if os.path.exists(path) and os.path.getsize(path) > 64:
        return open(path, "rb").read()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                data = r.read()
            if len(data) <= 64 and data.startswith(b"error code"):
                raise urllib.error.URLError(data.decode())
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
            return data
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == tries - 1:
                raise RuntimeError("%s: %s" % (url, e))
            time.sleep(2 + 3 * attempt)


def casc(cache, fdid):
    return fetch(CASC.format(fdid), os.path.join(cache, "casc", str(fdid)))


def casc_path(cache, fdid):
    casc(cache, fdid)
    return os.path.join(cache, "casc", str(fdid))


def db2(cache, table):
    """Retail DB2 table as {ID: row dict} (latest build)."""
    text = fetch(DB2.format(table), os.path.join(cache, "db2", table + ".csv")).decode("utf-8")
    return {r["ID"]: r for r in csv.DictReader(io.StringIO(text))}


def db2_rows(cache, table):
    text = fetch(DB2.format(table), os.path.join(cache, "db2", table + ".csv")).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def listfile(cache, wanted, prefixes=None):
    """{fdid: path} for the file data ids in wanted, or the paths under the given prefixes."""
    path = os.path.join(cache, "community-listfile.csv")
    fetch(LISTFILE, path)
    wanted = {str(x) for x in wanted or ()}
    prefixes = tuple(prefixes or ())
    out = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            i, _, p = line.rstrip("\n").partition(";")
            if i in wanted or (prefixes and p.startswith(prefixes)):
                out[int(i)] = p
    return out
