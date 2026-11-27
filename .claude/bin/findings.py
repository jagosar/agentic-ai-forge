"""Findings: the tier of a judge's finding, the plan's waivers, and whether a finding blocks.

One scale for every judge (both reviewers, QA, the test-auditor): floor never ships, reflex (a breach of a written
rule) blocks unless a waiver of the plan covers it, finish never blocks. A fingerprint names a finding across
reviews, so a re-review can say whether a fix addressed it. A finding with no tier keeps the meaning it
had before tiers existed: it blocks when its severity is one of the blocking ones. Pure functions, no imports from the
flow, so the bench and the engines' tests can load this module alone.
"""
import re

TIERS = ("floor", "reflex", "finish")
SUM_MODULUS = 1000000007
FNV_OFFSET = 2166136261
FNV_PRIME = 16777619
HASH_MASK = 0xFFFFFFFF
PROBLEM_CHARS = 80
FINGERPRINT_PARTS = ("axis", "tier", "rule", "file")
# A whole path in a text, as attribute() matches it, with an ASCII word class so the workflow's mirror agrees.
PATH_BEFORE = r"(?<![A-Za-z0-9_./-])"
PATH_AFTER = r"(?![A-Za-z0-9_-])"
ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
QA_NOT_RUN_DETAIL = 'QA did not run: the environment refused its commands (see the pending items of kind "qa not run")'
QA_NOT_RUN_FACT = "not run: the environment refused it"
PATH_SEPARATORS = re.compile(r"\s*[,;]\s*")  # a reviewer may join several paths into one `file`
PIN_ZONES = ("AT", "QA")  # the zones whose tests may pin a line (design 0036)
QA_ID_RE_TEMPLATE = r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"  # a defect id as a whole word, ASCII case folded
TRIAGED = ("quality", "acceptance")  # phases never triaged: their failures are never QA's tests
QA_TRIAGE_MAX_LINES = 10  # as verification.MAX_FAILING_LINES: a full list may hide more failures
PIN_PATH = r"[A-Za-z0-9_.@-]+(?:/[A-Za-z0-9_.@-]+)*"  # a repo-relative path the gate can pass unquoted
PIN_MAX_ARGS = 40  # arguments of one pinned call, so the command stays short
ACCEPTANCE_CONFLICT_DECISION = (
    "the fix would break the acceptance test that pins this line's text: change the test to check behaviour, "
    "or waive this rule for this file in the plan's waivers")


def tier_of(item, blocking):
    """item["tier"] when it is one of TIERS; else "floor" for a blocking severity, "finish" otherwise."""
    tier = item.get("tier") if isinstance(item, dict) else None
    if tier in TIERS:
        return tier
    severity = item.get("severity") if isinstance(item, dict) else None
    return "floor" if severity in blocking else "finish"


def in_scope(path, scope):
    """path is the scope, or lies under it when the scope ends in "/"."""
    if not isinstance(path, str) or not isinstance(scope, str) or not scope:
        return False
    return path.startswith(scope) if scope.endswith("/") else path == scope


def _rule_key(text):
    return text.strip().casefold() if isinstance(text, str) else ""


def waiver_for(item, waivers):
    """The first waiver that covers a reflex finding (its file in the scope, the rule names agree), or None."""
    if not isinstance(item, dict) or item.get("tier") != "reflex":
        return None
    rule = _rule_key(item.get("rule"))
    if not rule:
        return None
    for waiver in waivers or ():
        if not isinstance(waiver, dict):
            continue
        named = _rule_key(waiver.get("rule"))
        if named and (named in rule or rule in named) and in_scope(item.get("file"), waiver.get("scope")):
            return waiver
    return None


def blocks(item, blocking, waivers=()):
    """floor: True; reflex: True unless a waiver covers it; finish: False."""
    tier = tier_of(item, blocking)
    if tier == "reflex":
        return waiver_for(item, waivers) is None
    return tier == "floor"


def text_sum(text):
    """The sum of the code points of text, modulo 1000000007: a check that a long text arrived whole."""
    total = 0
    for ch in text:
        total = (total + ord(ch)) % SUM_MODULUS
    return total


def _part(finding, key):
    value = finding.get(key)
    return "" if value is None else str(value)


def fingerprint(finding):
    """"F" + 8 hex digits of FNV-1a (32-bit) over the code points of "<axis>|<tier>|<rule>|<file>|<problem>": the
    problem stripped of " \\t\\r\\n", lowered with str.lower() (as JS toLowerCase) and cut to its first 80 code points.
    The line and the evidence are left out: they change between reviews of the same finding."""
    problem = _part(finding, "problem").strip(" \t\r\n").lower()[:PROBLEM_CHARS]
    text = "|".join([_part(finding, k) for k in FINGERPRINT_PARTS] + [problem])
    h = FNV_OFFSET
    for ch in text:
        h = ((h ^ ord(ch)) * FNV_PRIME) & HASH_MASK
    return f"F{h:08x}"


def with_fingerprints(findings):
    """Copies of the findings, each with "fingerprint"; the second and later of a repeated value get "-2", "-3"."""
    seen, out = {}, []
    for f in findings:
        fp = fingerprint(f)
        seen[fp] = seen.get(fp, 0) + 1
        out.append({**f, "fingerprint": fp if seen[fp] == 1 else f"{fp}-{seen[fp]}"})
    return out


def _text(value):
    return value if isinstance(value, str) else ""


def _without_root(text, root):
    """text with "\\" read as "/" and every "<root>/" removed, the root compared ASCII-lowercased (a drive letter of
    another case still matches); the rest keeps its case."""
    text = text.replace("\\", "/")
    if not root:
        return text
    needle, low = (root.replace("\\", "/") + "/").translate(ASCII_LOWER), text.translate(ASCII_LOWER)
    out, i = [], 0
    while True:
        j = low.find(needle, i)
        if j < 0:
            return "".join(out) + text[i:]
        out.append(text[i:j])
        i = j + len(needle)


def _named(files, low):
    """The files (as written) whose whole path appears in the lowered text; a path ending in "/" names a directory."""
    return [f for f in files if isinstance(f, str) and f and re.search(
        PATH_BEFORE + re.escape(f.translate(ASCII_LOWER)) + ("" if f.endswith("/") else PATH_AFTER), low)]


def _paths(file, root):
    """The paths of a finding's `file`: root removed, split on "," and ";", empty and repeated pieces dropped."""
    if not isinstance(file, str):
        return []
    out = []
    for piece in PATH_SEPARATORS.split(_without_root(file, root)):
        if piece and piece not in out:
            out.append(piece)
    return out


def _owner_of(path, owners):
    """The first package, in id order, whose files hold the path (ASCII case folded; a "/" file is a folder)."""
    low = path.translate(ASCII_LOWER)
    for o in sorted(owners):
        files = owners[o] if isinstance(owners[o], list) else []
        for f in files:
            if not isinstance(f, str) or not f:
                continue
            fl = f.translate(ASCII_LOWER)
            if low == fl or (fl.endswith("/") and low.startswith(fl)):
                return o
    return None


def _original(f, wp, new_wp, paths, by_owner, unowned, mine):
    """The finding kept on its (possibly corrected) package, with "scope" and, when corrected, "wp_from"."""
    corrected = new_wp != wp
    out = {**f, "wp": new_wp, "scope": sorted(set(by_owner.get(new_wp, []) + unowned + mine))}
    if corrected or len(paths) > 1:
        own = by_owner.get(new_wp) or paths
        out["file"] = own[0] if own else f.get("file")
        if paths and out["file"] != paths[0]:
            out.pop("line", None)
    if corrected:
        out["wp_from"] = wp
    return out


def split_by_owner(findings, owners, root):
    """One axis's confirmed findings, each with "fingerprint". Its `file` is read path by path. A finding whose wp
    owns none of its owned paths goes to the owner of the first one ("wp_from" keeps the reviewer's). Every other
    package that owns a path of `file`, or whose files the evidence or fix names, gets a part in ascending id order,
    with that package's "wp", "file", "scope" and "split_from", no "line", and its own fingerprint (suffixed -2,
    -3 ... when taken). A finding with one path, on its owner, that names no other package is the same object."""
    owners = owners if isinstance(owners, dict) else {}
    root = root if isinstance(root, str) else ""
    taken = {f.get("fingerprint") for f in findings if isinstance(f, dict)}
    out = []
    for f in findings:
        if not isinstance(f, dict):
            out.append(f)
            continue
        wp = f.get("wp") if isinstance(f.get("wp"), str) else None
        paths = _paths(f.get("file"), root)
        by_owner, unowned = {}, []
        for path in paths:
            o = _owner_of(path, owners)
            (by_owner.setdefault(o, []) if o else unowned).append(path)
        new_wp = next(iter(by_owner)) if by_owner and wp not in by_owner else wp
        low = _without_root(_text(f.get("evidence")) + "\n" + _text(f.get("fix")), root).translate(ASCII_LOWER)
        others = {}
        for o in sorted(owners):
            if o == new_wp or not isinstance(owners[o], list):
                continue
            files = sorted(set(by_owner.get(o, []) + _named(owners[o], low)))
            if files:
                others[o] = files
        if new_wp == wp and not others and len(paths) <= 1:
            out.append(f)
            continue
        mine = _named(owners[new_wp], low) if isinstance(owners.get(new_wp), list) else []
        out.append(_original(f, wp, new_wp, paths, by_owner, unowned, mine))
        out.extend(_parts(f, others, taken))
    return out


def _parts(f, others, taken):
    """One part per other owning package: its files, no line, no wp_from, a fingerprint not yet taken."""
    parts = []
    for o, scope in others.items():
        part = {**f, "wp": o, "file": scope[0], "scope": scope, "split_from": f.get("fingerprint")}
        part.pop("line", None)
        part.pop("wp_from", None)
        base = fp = fingerprint(part)
        n = 2
        while fp in taken:
            fp, n = f"{base}-{n}", n + 1
        part["fingerprint"] = fp
        taken.add(fp)
        parts.append(part)
    return parts

def qa_environment_blocked(qa):
    """QA's report says the environment, not the code, kept it from validating."""
    return isinstance(qa, dict) and qa.get("status") == "BLOCKER" and qa.get("blocker_kind") == "environment"


def qa_not_run_items(qa):
    """The pending items of an environment-blocked QA report: one per command it could not run (strings, once each,
    in order), or one for QA's whole validation when it named none. [] for any other report."""
    if not qa_environment_blocked(qa):
        return []
    listed = qa.get("not_run") if isinstance(qa.get("not_run"), list) else []
    commands = []
    for cmd in listed:
        if isinstance(cmd, str) and cmd not in commands:
            commands.append(cmd)
    if not commands:
        return [_not_run_item("QA's validation", "allow QA's test commands, then run /implement again")]
    return [_not_run_item(cmd, "run " + cmd) for cmd in commands]


def _not_run_item(cmd, how):
    return {"type": "needs validation", "source": "qa", "wp": None, "file": None, "kind": "qa not run",
            "problem": cmd, "claim": cmd, "fact": QA_NOT_RUN_FACT, "how_to_check": how}


def pin_path(finding, root):
    """The repo-relative path of a Standards reflex finding that may be pinned by an acceptance test: it has a line
    (a real integer from 1) and a path the gate can pass as an argument. None for any other finding."""
    if not isinstance(finding, dict) or finding.get("tier") != "reflex":
        return None
    line, file = finding.get("line"), finding.get("file")
    if isinstance(line, bool) or not isinstance(line, int) or line < 1 or not isinstance(file, str) or not file:
        return None
    path = _without_root(file, root if isinstance(root, str) else "")
    if not re.fullmatch(PIN_PATH, path) or set(path.split("/")) & {".", ".."}:
        return None
    return path


def pinned_args(findings, root):
    """FILE:LINE for each finding that may be pinned, once each and in order, the first PIN_MAX_ARGS."""
    args = []
    for f in findings:
        path = pin_path(f, root)
        if path and f"{path}:{f['line']}" not in args:
            args.append(f"{path}:{f['line']}")
    return args[:PIN_MAX_ARGS]


def _usable_pin(pin):
    ints = all(isinstance(pin.get(k), int) and not isinstance(pin.get(k), bool) for k in ("line", "test_line"))
    return isinstance(pin, dict) and ints and all(isinstance(pin.get(k), str) for k in ("file", "test", "text"))


def split_pinned(findings, root, answer):
    """(kept, pinned) of the findings, given the parsed answer of `agentic.py pinned` (or None). A pinned finding is
    a copy with "pinned_by": {"test", "test_line", "text"}; the kept ones are the same objects. A malformed answer
    pins nothing."""
    listed = answer.get("pinned") if isinstance(answer, dict) else None
    pins = {(p["file"], p["line"]): p for p in listed or [] if isinstance(p, dict) and _usable_pin(p)}
    wanted = set(pinned_args(findings, root))
    kept, pinned = [], []
    for f in findings:
        path = pin_path(f, root)
        pin = pins.get((path, f["line"])) if path and f"{path}:{f['line']}" in wanted else None
        if pin:
            by = {"test": pin["test"], "test_line": pin["test_line"], "text": pin["text"]}
            if pin.get("zone") in PIN_ZONES:
                by["zone"] = pin["zone"]
            pinned.append({**f, "pinned_by": by})
        else:
            kept.append(f)
    return kept, pinned


def conflict_item(finding):
    """The pending item of a pinned finding: the finding, no fix attempted, and what a person can do."""
    return {"type": "acceptance conflict", "source": "standards-reviewer", **finding,
            "decision": ACCEPTANCE_CONFLICT_DECISION}


def _triage_lines(phase):
    """A failing phase's lines for the triage: new_failures, else failing_lines; never its tail."""
    for key in ("new_failures", "failing_lines"):
        value = phase.get(key)
        if isinstance(value, list) and value:
            return [x for x in value if isinstance(x, str)]
    return []


def _qa_lists(qa):
    """(open defects [{"id", "wp"}], red test names) of a QA report."""
    defects = qa.get("defects") if isinstance(qa.get("defects"), list) else []
    open_ = [{"id": d["id"], "wp": d.get("wp")} for d in defects
             if isinstance(d, dict) and isinstance(d.get("id"), str)]
    reds = qa.get("red_tests") if isinstance(qa.get("red_tests"), list) else []
    red = [t["test"] for t in reds if isinstance(t, dict) and isinstance(t.get("test"), str) and t["test"]]
    return open_, red


def _named_defects(name, lines, open_):
    """One verification defect per (wp, id) of an open QA defect whose id a line names as a whole word."""
    out, seen = [], set()
    for d in open_:
        if not isinstance(d["wp"], str) or (d["wp"], d["id"]) in seen:
            continue
        rx = re.compile(QA_ID_RE_TEMPLATE % re.escape(d["id"]), re.IGNORECASE | re.ASCII)
        hits = [line for line in lines if rx.search(line)]
        if hits:
            seen.add((d["wp"], d["id"]))
            out.append({"source": "verification", "severity": "high", "wp": d["wp"], "file": "",
                        "problem": f"verification fails ({name}) on QA's test of {d['id']}",
                        "evidence": (f"{name}: " + "\n".join(hits))[:1500]})
    return out


def qa_triage(verification, qa):
    """What QA's last report says about a failed verification: the failing lines that are tests QA left red on
    purpose ("known"), the phases made only of them ("cleared"), whether every blocking phase is cleared, defects for
    the open QA defects other lines name, and QA's open defects. Pure; never raises."""
    out = {"known": [], "cleared": [], "all_cleared": False, "defects": [], "open": []}
    if not isinstance(qa, dict):
        return out
    out["open"], red = _qa_lists(qa)
    phases = verification.get("phases") if isinstance(verification, dict) else None
    for p in phases if isinstance(phases, list) else []:
        if not isinstance(p, dict) or p.get("status") not in ("regression", "fails") or p.get("name") in TRIAGED:
            continue
        name, lines = str(p.get("name")), _triage_lines(p)
        known = [line for line in lines if any(t in line for t in red)]
        out["known"] += [{"phase": name, "line": line} for line in known]
        if lines and len(known) == len(lines) and len(lines) < QA_TRIAGE_MAX_LINES:
            out["cleared"].append(name)
        taken = {(d["wp"], d["problem"]) for d in out["defects"]}
        out["defects"] += [d for d in _named_defects(name, [x for x in lines if x not in known], out["open"])
                           if (d["wp"], d["problem"]) not in taken]
    blocking = verification.get("blocking") if isinstance(verification, dict) else None
    out["all_cleared"] = isinstance(blocking, list) and bool(blocking) and all(b in out["cleared"] for b in blocking)
    return out
