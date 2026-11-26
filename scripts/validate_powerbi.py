"""Structural validation of the PBIP project (no Power BI Desktop needed).
Checks: every JSON parses; every field a visual uses exists in the TMDL model; measures reference only existing
measures/columns; visuals stay inside the page; page order is consistent; no personal absolute paths.
Optional: --schemas DIR validates visual/page/report JSON against Microsoft's published JSON schemas (downloaded copy).
Exit code 0 = all checks passed.  NOTE: passing proves structure, NOT that Power BI Desktop renders it."""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJ = ROOT / "powerbi" / "ROIP_PowerBI_Project"
SM = PROJ / "ROIP_Operations_Intelligence.SemanticModel" / "definition"
RP = PROJ / "ROIP_Operations_Intelligence.Report" / "definition"


def parse_model():
    tables, measures = {}, {}
    for f in (SM / "tables").glob("*.tmdl"):
        txt = f.read_text(encoding="utf-8")
        name = re.match(r"table (\S+)", txt).group(1).strip("'")
        cols = {m.strip("'") for m in re.findall(r"^\tcolumn (.+)$", txt, flags=re.M)}
        tables[name] = cols
        for m in re.finditer(r"^\tmeasure (.+?) =", txt, flags=re.M):
            measures[m.group(1).strip("'")] = txt
    return tables, measures


def field_refs(obj, out):
    if isinstance(obj, dict):
        for k in ("Column", "Measure"):
            if k in obj:
                out.append((k, obj[k]["Expression"]["SourceRef"]["Entity"], obj[k]["Property"]))
        for v in obj.values():
            field_refs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            field_refs(v, out)


def run(schemas=None):
    errors, info = [], {}
    tables, measures = parse_model()
    info["tables"], info["measures"] = sorted(tables), len(measures)
    # measure bodies: [Measure] references must exist; table[col] references must exist
    meas_txt = (SM / "tables" / "operations_clean.tmdl").read_text(encoding="utf-8")
    for m in re.finditer(r"^\tmeasure (.+?) =(.*?)(?=^\t(?:measure|column|partition)|\Z)", meas_txt, flags=re.M | re.S):
        body = m.group(2)
        for ref in re.findall(r"(?<![A-Za-z0-9_'])\[([^\]]+)\]", body):
            if ref not in measures and not any(ref in c for c in tables.values()) and ref not in ("@v",):
                errors.append(f"measure {m.group(1)} references unknown [{ref}]")
        for t, c in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\[([^\]]+)\]", body):
            if t in tables and c not in tables[t]:
                errors.append(f"measure {m.group(1)} references unknown column {t}[{c}]")
    # JSON files + visuals
    n_vis = 0
    page_order = json.loads((RP / "pages" / "pages.json").read_text())["pageOrder"]
    pages = {p.name: json.loads((p / "page.json").read_text()) for p in (RP / "pages").iterdir() if p.is_dir()}
    if sorted(page_order) != sorted(pages):
        errors.append("pages.json pageOrder does not match page folders")
    for pname, page in pages.items():
        names = set()
        for vf in (RP / "pages" / pname / "visuals").glob("*/visual.json"):
            v = json.loads(vf.read_text()); n_vis += 1
            if v["name"] in names: errors.append(f"duplicate visual name {v['name']}")
            names.add(v["name"])
            pos = v["position"]
            if pos["x"] < 0 or pos["y"] < 0 or pos["x"] + pos["width"] > page["width"] + 1 or pos["y"] + pos["height"] > page["height"] + 1:
                errors.append(f"visual outside page: {pname}/{v['name']} {pos}")
            refs = []; field_refs(v, refs)
            for kind, ent, prop in refs:
                if ent not in tables: errors.append(f"unknown table {ent} in {v['name']}")
                elif kind == "Column" and prop not in tables[ent]: errors.append(f"unknown column {ent}[{prop}] in {v['name']}")
                elif kind == "Measure" and prop not in measures: errors.append(f"unknown measure [{prop}] in {v['name']}")
    info["pages"], info["visuals"] = len(pages), n_vis
    # no personal paths / secrets anywhere in the project
    for f in PROJ.rglob("*"):
        if f.is_file() and f.suffix in {".tmdl", ".json", ".pbip", ".pbir", ".pbism", ".md"}:
            t = f.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"C:\\Users\\(?!\\)[A-Za-z]", t) or "Rishi Parmani" in t:
                errors.append(f"personal absolute path in {f.relative_to(PROJ)}")
    if schemas:
        errors += schema_check(Path(schemas))
    return errors, info


def schema_check(sdir: Path):
    """Resolve Microsoft schema URIs to a local copy: <sdir>/<name>_<version>.json or <sdir>/refs/<name>/<version>/*.json."""
    import jsonschema
    from referencing import Registry, Resource

    def local(uri: str) -> Path:
        parts = [p for p in uri.split("/") if p]
        fname = parts[-1]; ver = parts[-2]; name = parts[-3]
        top = sdir / f"report_definition_{name}_{ver}.json"
        if top.exists():
            return top
        ref = sdir / "refs" / name / ver / fname
        if ref.exists():
            return ref
        raise LookupError(uri)

    def retrieve(uri):
        return Resource.from_contents(json.loads(local(uri).read_text()))

    reg = Registry(retrieve=retrieve)
    errs, checked = [], 0
    for f in RP.rglob("*.json"):
        d = json.loads(f.read_text())
        if "$schema" not in d:
            continue
        try:
            sch = json.loads(local(d["$schema"]).read_text())
            sch.setdefault("$id", d["$schema"])
            v = jsonschema.Draft7Validator(sch, registry=reg)
            for e in list(v.iter_errors(d))[:3]:
                errs.append(f"schema violation {f.relative_to(RP)}: {e.message[:160]}")
            checked += 1
        except LookupError as e:
            errs.append(f"schema not available locally for {f.name}: {e}")
    print(f"schema-validated {checked} JSON files")
    return errs


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--schemas")
    a = ap.parse_args()
    errs, info = run(a.schemas)
    print(json.dumps(info, indent=1))
    print("ERRORS:" if errs else "ALL CHECKS PASSED")
    for e in errs[:40]: print(" -", e)
    sys.exit(1 if errs else 0)
