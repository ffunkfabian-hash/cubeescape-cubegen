#!/usr/bin/env python3
"""Release a Cubegen version: the manual steps of AGENTS.md › "Versionen, Branches und Worktrees" as one command.

    python3 tools/release.py                      # dry run: every check, then the plan (nothing changes)
    python3 tools/release.py --apply              # merge, tag, push
    python3 tools/release.py --apply --trailer "Co-Authored-By: Name <mail>"

Run it from the release worktree (branch ``release/<version>``) or anywhere in the repository with ``--branch``.
What is checked and merged is the release branch as committed (files read with ``git show``); the main checkout is
found through ``git worktree list`` (the worktree that has ``main``) - it is never switched to another branch.

Checks (all of them, also in a dry run; any error stops ``--apply`` before the first change):

- version: the same in ``pyproject.toml``, ``cubegen/__init__.py`` and the add-on's ``bl_info``; ``CHANGELOG.md`` has
  ``## <version> „<Name>“ – <YYYY-MM-DD>`` (a date, not "unveröffentlicht"); ``VERSION_<version>.md`` exists, is
  titled ``# Cubegen <version> – <Name>`` and is no longer marked "ungeprüft";
- branches: the release branch is called ``release/<version>``, its worktree (if any) and the main checkout are clean, ``main`` equals
  ``<remote>/main`` after a fetch (``--no-fetch``: the last known state) and is part of the release branch (the merge
  can't conflict); tag ``v<version>`` exists neither here nor on the remote; a release branch on the remote is
  part of the local one (the push needs no force);
- content of everything the push would send (objects of the release branch not on ``<remote>/main``): no file over
  100 MB (GitHub refuses them; over 50 MB is a warning) and nothing that looks like a credential - private keys,
  GitHub / AWS / Slack / OpenAI / Anthropic / Google tokens, passwords in URLs, files such as ``.env``, ``id_rsa``,
  ``*.pem``, ``*.p12``, ``.netrc``, ``.pypirc`` (findings name file and line, never the value).

``--apply`` then, in the main checkout: ``git merge --no-ff release/<version> -m "Cubegen <version> – Release
übernehmen"`` (plus ``--trailer`` lines), ``git tag -a v<version> -m "Cubegen <version> – <Name>"``, ``git push
--atomic <remote> main release/<version> v<version>`` - never ``--force``: all three refs or none. Finally the links
(release branch, tag, compare with the previous tag). A failed push leaves merge and tag local; the message says how
to push again or undo.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

LIMIT = 100 * 1024 * 1024   # GitHub refuses files over 100 MB
WARN = 50 * 1024 * 1024     # and warns from 50 MB
SCAN_LIMIT = 2 * 1024 * 1024  # bigger blobs are data (models, images), not scanned for credentials
MERGE_MESSAGE = "Cubegen {version} – Release übernehmen"
TAG_MESSAGE = "Cubegen {version} – {name}"

#: (what, pattern) - a match is reported with file and line, never with its text
SECRET_PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("privater Schlüssel", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY(?: BLOCK)?-----")),
    ("GitHub-Token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b")),
    ("AWS-Zugangsschlüssel", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack-Token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Anthropic-Schlüssel", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI-Schlüssel", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}")),
    ("Google-API-Schlüssel", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Passwort in einer URL", re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@'\"]+:[^/\s:@'\"]{3,}@[A-Za-z0-9.-]+")),
]
SECRET_FILES = re.compile(r"(^|/)(\.env(\.[^/]*)?|id_(rsa|dsa|ecdsa|ed25519)|\.netrc|\.pypirc|credentials(\.json)?|"
                          r"[^/]*\.(pem|p12|pfx|key|keystore|jks|mobileprovision))$", re.IGNORECASE)
SECRET_FILES_OK = re.compile(r"(^|/)\.env\.(example|sample|template)$", re.IGNORECASE)


class ReleaseError(RuntimeError):
    pass


def git(cwd: str, *args: str, check: bool = True, input_data: Optional[bytes] = None) -> str:
    proc = subprocess.run(["git", "-C", cwd, *args], input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)}: {proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout.decode("utf-8", "replace")


def git_ok(cwd: str, *args: str) -> bool:
    return subprocess.run(["git", "-C", cwd, *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


@dataclass
class Report:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passed: List[str] = field(default_factory=list)

    def check(self, ok: bool, good: str, bad: str) -> bool:
        (self.passed if ok else self.errors).append(good if ok else bad)
        return ok


# --- what is released ------------------------------------------------------------------------------------------------

def show(cwd: str, branch: str, rel: str) -> Optional[str]:
    """``rel`` as the release branch has it (committed - what gets merged), None when missing."""
    proc = subprocess.run(["git", "-C", cwd, "show", f"{branch}:{rel}"], stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL)
    return proc.stdout.decode("utf-8", "replace") if proc.returncode == 0 else None


def versions(cwd: str, branch: str) -> Dict[str, Optional[str]]:
    """The version in its three places on ``branch`` (None where it can't be read)."""
    found: Dict[str, Optional[str]] = {}
    for label, rel, pattern in (("pyproject.toml", "pyproject.toml", r'^version\s*=\s*"([^"]+)"'),
                                ("cubegen/__init__.py", "cubegen/__init__.py", r'^__version__\s*=\s*"([^"]+)"'),
                                ("bl_info", "blender_addon/cubegen_addon/__init__.py",
                                 r'"version":\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')):
        match = re.search(pattern, show(cwd, branch, rel) or "", re.MULTILINE)
        found[label] = ".".join(match.groups()) if match else None
    return found


def changelog_entry(text: str, version: str) -> Tuple[Optional[str], Optional[str]]:
    """(name, date) of ``## <version> „<Name>“ – <date>`` in CHANGELOG.md; date None for "unveröffentlicht"."""
    match = re.search(rf"^## {re.escape(version)} „([^“]+)“ – (\S+)", text, re.MULTILINE)
    if not match:
        return None, None
    date = match.group(2) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", match.group(2)) else None
    return match.group(1), date


# --- repositories ----------------------------------------------------------------------------------------------------

def worktrees(cwd: str) -> List[Dict[str, str]]:
    found, current = [], {}
    for line in git(cwd, "worktree", "list", "--porcelain").splitlines():
        if not line:
            if current:
                found.append(current)
            current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        found.append(current)
    return found


def checkout_of(cwd: str, branch: str) -> Optional[str]:
    """The worktree that has ``branch`` checked out (None: none has)."""
    for tree in worktrees(cwd):
        if tree.get("branch") == f"refs/heads/{branch}":
            return tree["worktree"]
    return None


def github_url(remote_url: str) -> Optional[str]:
    """https://github.com/<owner>/<repo> of a GitHub remote (https or ssh), else None."""
    match = re.match(r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+)/(.+?)(?:\.git)?/?$",
                     remote_url.strip())
    return f"https://github.com/{match.group(1)}/{match.group(2)}" if match else None


def previous_tag(cwd: str, ref: str, tag: str) -> Optional[str]:
    out = git(cwd, "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*", f"{ref}^", check=False).strip()
    return out if out and out != tag else None


# --- what the push sends ---------------------------------------------------------------------------------------------

def pushed_blobs(cwd: str, branch: str, exclude: List[str]) -> List[Tuple[str, int, str]]:
    """(sha, size, path) of every blob reachable from ``branch`` and from none of ``exclude``."""
    args = ["rev-list", "--objects", branch] + [f"^{ref}" for ref in exclude]
    paths: Dict[str, str] = {}
    for line in git(cwd, *args).splitlines():
        sha, _, path = line.partition(" ")
        if sha and sha not in paths:
            paths[sha] = path
    if not paths:
        return []
    out = git(cwd, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
              input_data="\n".join(paths).encode() + b"\n")
    blobs = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] == "blob":
            blobs.append((parts[0], int(parts[2]), paths[parts[0]]))
    return blobs


def blob_text(cwd: str, sha: str) -> Optional[str]:
    data = subprocess.run(["git", "-C", cwd, "cat-file", "blob", sha], stdout=subprocess.PIPE).stdout
    if b"\0" in data[:8192]:
        return None  # binary
    return data.decode("utf-8", "replace")


def scan_secrets(cwd: str, blobs: List[Tuple[str, int, str]]) -> List[str]:
    found = []
    for sha, size, path in blobs:
        if SECRET_FILES.search(path) and not SECRET_FILES_OK.search(path):
            found.append(f"{path}: Dateiname einer Zugangsdatei")
        if size > SCAN_LIMIT:
            continue
        text = blob_text(cwd, sha)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for what, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    found.append(f"{path}:{number}: sieht aus wie ein {what}")
    return found


# --- the release -----------------------------------------------------------------------------------------------------

@dataclass
class Plan:
    version: str = ""
    name: str = ""
    branch: str = ""
    tag: str = ""
    main_dir: str = ""
    remote: str = "origin"
    main: str = "main"
    trailers: List[str] = field(default_factory=list)
    url: Optional[str] = None
    previous: Optional[str] = None

    def merge_message(self) -> str:
        message = MERGE_MESSAGE.format(version=self.version)
        return message + ("\n\n" + "\n".join(self.trailers) if self.trailers else "")

    def commands(self) -> List[List[str]]:
        return [["git", "-C", self.main_dir, "merge", "--no-ff", self.branch, "-m", self.merge_message()],
                ["git", "-C", self.main_dir, "tag", "-a", self.tag, "-m",
                 TAG_MESSAGE.format(version=self.version, name=self.name)],
                ["git", "-C", self.main_dir, "push", "--atomic", self.remote, self.main, self.branch, self.tag]]

    def links(self) -> List[str]:
        if not self.url:
            return []
        links = [f"Release-Zweig: {self.url}/tree/{self.branch}", f"Tag: {self.url}/releases/tag/{self.tag}"]
        if self.previous:
            links.append(f"Vergleich: {self.url}/compare/{self.previous}...{self.tag}")
        return links


def check(checkout: str, branch: Optional[str] = None, remote: str = "origin", main: str = "main", fetch: bool = True,
          trailers: Optional[List[str]] = None) -> Tuple[Plan, Report]:
    """Every check; the plan is complete when the report has no errors. ``branch``: the release branch (default:
    the one checked out in ``checkout``); its committed files are what is checked and merged."""
    report = Report()
    checkout = git(checkout, "rev-parse", "--show-toplevel").strip()
    plan = Plan(remote=remote, main=main, trailers=list(trailers or []))
    current = git(checkout, "rev-parse", "--abbrev-ref", "HEAD").strip()
    branch = branch or current
    if not branch.startswith("release/") or not git_ok(checkout, "rev-parse", "--verify", "--quiet",
                                                         f"refs/heads/{branch}"):
        raise ReleaseError(f"kein Release-Zweig: {branch!r} - im Release-Worktree starten oder --branch release/<Version>")
    plan.branch = branch
    found = versions(checkout, branch)
    version = found["pyproject.toml"] or "?"
    report.check(version != "?" and len(set(found.values())) == 1,
                 f"Version {version} in pyproject.toml, cubegen/__init__.py und bl_info",
                 "Version nicht überall gleich: " + ", ".join(f"{k} {v}" for k, v in found.items()))
    report.check(branch == f"release/{version}", f"Zweig {branch} passt zur Version",
                 f"Zweig {branch} passt nicht zur Version {version} (release/{version})")
    plan.version, plan.tag = version, f"v{version}"
    name, date = changelog_entry(show(checkout, branch, "CHANGELOG.md") or "", version)
    plan.name = name or "?"
    report.check(bool(name), f"CHANGELOG: {version} „{name}“", f"CHANGELOG.md: kein Eintrag „## {version} „Name“ – …“")
    if name:
        report.check(bool(date), f"CHANGELOG-Datum {date}",
                     f"CHANGELOG.md: {version} hat kein Datum (noch „unveröffentlicht“?) - erst Datum eintragen und "
                     "committen")
    head = (show(checkout, branch, f"VERSION_{version}.md") or "").splitlines()
    title = head[0].strip() if head else ""
    if report.check(title == f"# Cubegen {version} – {plan.name}", f"VERSION_{version}.md: „{title[2:]}“",
                    f"VERSION_{version}.md fehlt oder hat nicht den Titel „# Cubegen {version} – {plan.name}“"):
        report.check(not any("ungeprüft" in line for line in head[:6]), f"VERSION_{version}.md ohne Vermerk "
                     "„ungeprüft“", f"VERSION_{version}.md ist noch als „ungeprüft“ markiert (Stufe 2 fehlt)")

    main_dir = checkout_of(checkout, main)
    plan.main_dir = main_dir or ""
    if not report.check(bool(main_dir), f"Haupt-Checkout {main_dir}",
                        f"kein Checkout hat {main} ausgecheckt (git worktree list)"):
        return plan, report
    release_dir = checkout_of(checkout, branch)
    if release_dir:
        report.check(not git(release_dir, "status", "--porcelain").strip(), f"Release-Worktree sauber ({release_dir})",
                     f"Release-Worktree {release_dir} hat offene Änderungen - committen oder verwerfen")
    report.check(not git(main_dir, "status", "--porcelain").strip(), f"Haupt-Checkout sauber ({main})",
                 f"Haupt-Checkout {main_dir} hat offene Änderungen - der Merge würde sie mischen")

    remote_url = git(checkout, "remote", "get-url", remote, check=False).strip()
    if not report.check(bool(remote_url), f"Remote {remote}: {remote_url}", f"Remote {remote} fehlt"):
        return plan, report
    plan.url = github_url(remote_url)
    if fetch:
        try:
            git(checkout, "fetch", "--quiet", "--tags", remote)
            report.passed.append(f"git fetch {remote}")
        except ReleaseError as exc:
            report.errors.append(f"git fetch {remote} fehlgeschlagen: {exc}")
    remote_main = f"refs/remotes/{remote}/{main}"
    has_remote_main = git_ok(checkout, "rev-parse", "--verify", "--quiet", remote_main)
    if has_remote_main:
        same = git(checkout, "rev-parse", main).strip() == git(checkout, "rev-parse", remote_main).strip()
        report.check(same, f"{main} = {remote}/{main}",
                     f"{main} weicht von {remote}/{main} ab - erst abgleichen (git pull im Haupt-Checkout)")
    else:
        report.warnings.append(f"{remote}/{main} unbekannt (neues Repository?)")
    report.check(git_ok(checkout, "merge-base", "--is-ancestor", main, branch),
                 f"{main} ist in {branch} enthalten (Merge ohne Konflikte)",
                 f"{main} ist nicht in {branch} enthalten - erst {main} in den Release-Zweig mergen und prüfen")
    report.check(not git_ok(checkout, "rev-parse", "--verify", "--quiet", f"refs/tags/{plan.tag}"),
                 f"Tag {plan.tag} noch frei", f"Tag {plan.tag} gibt es schon")
    if fetch:
        remote_tags = git(checkout, "ls-remote", "--tags", remote, f"refs/tags/{plan.tag}", check=False).strip()
        report.check(not remote_tags, f"Tag {plan.tag} auf {remote} frei", f"Tag {plan.tag} gibt es auf {remote} schon")
    remote_branch = f"refs/remotes/{remote}/{branch}"
    has_remote_branch = git_ok(checkout, "rev-parse", "--verify", "--quiet", remote_branch)
    if has_remote_branch:
        report.check(git_ok(checkout, "merge-base", "--is-ancestor", remote_branch, branch),
                     f"{remote}/{branch} ist im lokalen Zweig enthalten (Push ohne --force)",
                     f"{remote}/{branch} hat Commits, die lokal fehlen - der Push bräuchte --force (verboten)")

    exclude = ([remote_main] if has_remote_main else []) + ([remote_branch] if has_remote_branch else [])
    blobs = pushed_blobs(checkout, branch, exclude)
    too_big = [f"{path} ({size / 2 ** 20:.0f} MB)" for _, size, path in blobs if size > LIMIT]
    report.check(not too_big, f"keine Datei über 100 MB ({len(blobs)} neue Dateistände geprüft)",
                 "Dateien über 100 MB (GitHub lehnt sie ab): " + ", ".join(too_big))
    report.warnings += [f"{path}: {size / 2 ** 20:.0f} MB (GitHub warnt ab 50 MB)" for _, size, path in blobs
                        if WARN < size <= LIMIT]
    secrets = scan_secrets(checkout, blobs)
    report.check(not secrets, "keine Zugangsdaten gefunden", "mögliche Zugangsdaten: " + "; ".join(secrets))
    plan.previous = previous_tag(checkout, branch, plan.tag)
    return plan, report


def apply(plan: Plan, out=print) -> None:
    merge, tag, push = plan.commands()
    for step, cmd in (("Merge", merge), ("Tag", tag)):
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0:
            raise ReleaseError(f"{step} fehlgeschlagen:\n{proc.stdout.strip()}")
        out(f"{step}: ok")
    proc = subprocess.run(push, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise ReleaseError(
            f"Push fehlgeschlagen (nichts gepusht, --atomic):\n{proc.stdout.strip()}\nMerge und Tag liegen lokal in "
            f"{plan.main_dir}. Erneut: {' '.join(push[3:])} - oder zurück: git -C {plan.main_dir} tag -d {plan.tag} "
            f"&& git -C {plan.main_dir} reset --hard ORIG_HEAD")
    out(f"Push: {plan.remote} {plan.main} {plan.branch} {plan.tag}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Release a Cubegen version (dry run unless --apply).")
    parser.add_argument("--apply", action="store_true", help="merge, tag and push (default: only check and plan)")
    parser.add_argument("--branch", help="release branch (default: the one checked out here)")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--main", default="main", help="the default branch (default: main)")
    parser.add_argument("--trailer", action="append", default=[],
                        help="line appended to the merge message, e.g. 'Co-Authored-By: …' (repeatable)")
    parser.add_argument("--no-fetch", action="store_true", help="don't fetch: compare with the last known remote")
    parser.add_argument("-C", dest="checkout", default=os.getcwd(), help="checkout to release from (default: here)")
    args = parser.parse_args(argv)
    try:
        plan, report = check(args.checkout, args.branch, args.remote, args.main, fetch=not args.no_fetch,
                             trailers=args.trailer)
    except ReleaseError as exc:
        print(f"Fehler: {exc}")
        return 1
    print(f"Cubegen {plan.version} „{plan.name}“ - {plan.branch} -> {plan.main} ({plan.main_dir})")
    for line in report.passed:
        print(f"  ok      {line}")
    for line in report.warnings:
        print(f"  Hinweis {line}")
    for line in report.errors:
        print(f"  FEHLER  {line}")
    if report.errors:
        print(f"{len(report.errors)} Fehler - kein Release.")
        return 1
    print("Plan:")
    for cmd in plan.commands():
        print("  " + " ".join(f"'{c}'" if (" " in c or "\n" in c) else c for c in cmd).replace("\n", "\\n"))
    if not args.apply:
        print("Probelauf - nichts geändert. Ausführen mit --apply.")
        for link in plan.links():
            print(f"  {link}")
        return 0
    try:
        apply(plan)
    except ReleaseError as exc:
        print(f"Fehler: {exc}")
        return 1
    for link in plan.links():
        print(f"  {link}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
