"""The flow's PreToolUse hook launcher: runs `agentic.py hook` from the repository's .claude/bin.

settings.json names this file, so it stays where projects expect it. It is never owned by a work package: an agent that
could edit it could replace the guard that judges it. Standard library only, no type annotations (Python 3.9), and
it never imports agentic.py at module level, so a broken agentic.py cannot break the launcher itself.

In a git worktree Claude Code keeps CLAUDE_PROJECT_DIR at the checkout the session started in, while the hook's JSON
gives the worktree as "cwd" (design 0034). The session's main thread is then judged by the worktree's own guard, and
the root it chose is remembered per session, so the session's agents are judged there too, whatever their own cwd.
"""
import io
import json
import os
import runpy
import sys
import time
from pathlib import Path

GITDIR_PREFIX = "gitdir:"  # the first line of a linked worktree's .git file
WORKTREES_DIR = "worktrees"  # a linked worktree's git dir is <common>/worktrees/<name>
FLOW_ENTRY = Path(".claude") / "bin" / "agentic.py"
SESSION_ROOTS = Path(".claude") / "state" / "worktree-roots.json"  # under the project (CLAUDE_PROJECT_DIR)
SESSION_ROOTS_MAX = 20  # sessions remembered; the oldest are dropped


def _gitdir_of(git_file):
    """The git dir a .git file points to, or None when it is not a "gitdir:" file."""
    first = git_file.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    if not first or not first[0].startswith(GITDIR_PREFIX):
        return None
    target = Path(first[0][len(GITDIR_PREFIX):].strip())
    return (target if target.is_absolute() else git_file.parent / target).resolve()


def _common_dir(checkout):
    """The repository's common git dir for a checkout (its .git folder, or what its .git file points to), or None."""
    git = Path(checkout) / ".git"
    if git.is_dir():
        return git.resolve()
    gitdir = _gitdir_of(git) if git.is_file() else None
    return gitdir.parent.parent if gitdir is not None and gitdir.parent.name == WORKTREES_DIR else None


def linked_worktree(start, project):
    """The root of the linked worktree holding `start`, when it belongs to the same repository as `project` and has
    the flow installed; None otherwise. Reads .git files only (no git process) and never raises."""
    try:
        here = Path(start).resolve()
        for d in [here, *here.parents]:
            git = d / ".git"
            if git.is_dir():
                return None
            if not git.is_file():
                continue
            gitdir = _gitdir_of(git)
            if gitdir is None or gitdir.parent.name != WORKTREES_DIR:
                return None
            common = _common_dir(project)
            same = common is not None and gitdir.parent.parent == common
            return d if same and (d / FLOW_ENTRY).is_file() else None
        return None
    except (OSError, ValueError):
        return None


def _text(payload, key):
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def remembered(project, session_id):
    """The root the session's main thread chose, or None."""
    try:
        data = json.loads((Path(project) / SESSION_ROOTS).read_text(encoding="utf-8"))
        entry = data.get(session_id) if isinstance(data, dict) else None
        root = entry.get("root") if isinstance(entry, dict) else None
        return Path(root) if isinstance(root, str) and root else None
    except (OSError, ValueError):
        return None


def remember(project, session_id, root):
    """Records (or, with root None, forgets) the session's root; written only when it changes. Errors are ignored:
    the session's agents then fall back to the project, today's behaviour."""
    path = Path(project) / SESSION_ROOTS
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        data = data if isinstance(data, dict) else {}
        old = data.get(session_id)
        if root is None and old is None:
            return
        if root is not None and isinstance(old, dict) and old.get("root") == str(root):
            return
        if root is None:
            data.pop(session_id, None)
        else:
            data[session_id] = {"root": str(root), "ts": time.time()}
        newest = sorted(data.items(), key=lambda kv: kv[1].get("ts", 0) if isinstance(kv[1], dict) else 0)
        data = dict(newest[-SESSION_ROOTS_MAX:])
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(str(tmp), str(path))
    except (OSError, ValueError):
        return


def choose_root(raw, project, env):
    """The root whose guard judges this call. A fallback agent (AGENTIC_WP) keeps the root its launcher set; an
    agent of the session is judged where the session's main thread chose; the main thread follows its cwd into a
    linked worktree of the same repository, and the choice is remembered for its session."""
    project = Path(project)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return project
    if not isinstance(payload, dict) or env.get("AGENTIC_WP"):
        return project
    session, cwd = _text(payload, "session_id"), _text(payload, "cwd")
    if _text(payload, "agent_id"):
        root = remembered(project, session) if session else None
        return root if root is not None and linked_worktree(root, project) == root.resolve() else project
    root = linked_worktree(cwd, project) if cwd else None
    if session:
        remember(project, session, root)
    return root if root is not None else project


def main():
    try:
        raw = sys.stdin.buffer.read()
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
        root = choose_root(raw, project, os.environ)
        script = root / FLOW_ENTRY
    except Exception as e:  # noqa: BLE001 - no guard can be chosen: fail closed
        print(f"[agentic hook.py] cannot choose the guard, blocked for safety: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
    if root != project:
        os.environ["CLAUDE_PROJECT_DIR"] = str(root)
    sys.stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")
    sys.argv = [str(script), "hook"]
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
