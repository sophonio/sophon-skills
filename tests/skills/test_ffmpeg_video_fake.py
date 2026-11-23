"""ffmpeg-video against a fake ffmpeg/ffprobe (generated at test time, see ffmpeg_video_fakes.py).

Runs on Windows and POSIX without FFmpeg. Every call goes through the real Sophon shape
(sandboxsim.run_process: preamble + main.py as script.py in a workspace folder):

- a fake reporting 5.1 gives DEPENDENCY_MISSING (preflight) with an upgrade fix;
- a fake 7.1 lets dry runs of cut, fit and export succeed and leaves the output root unchanged;
- doctor reports ready with the wrapper facts;
- a hanging fake under a manifest patched to timeoutSeconds 75 (deadline 15 s) gives a
  structured TIMEOUT well inside the limit, with no partial output, no lock or hidden sibling
  of this run, no temp folder and no fake process left behind, while an older lock is kept;
- a render whose check stage fails keeps the finished file and names it in `kept`, and a second
  identical use_cache render hits the stage cache;
- an output another call wrote after this one resolved its paths is refused (output_exists) and
  left alone.

Plain script, `ok  ` / `FAIL` lines: python tests/skills/test_ffmpeg_video_fake.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ffmpeg_video_fakes import make_fake_bin, pid_alive  # noqa: E402
from sandboxsim import FakeDataDir, base_env, run_process  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    print(f"{'ok  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  -- {str(detail)[:700]}"))
    ok &= bool(cond)
    return bool(cond)


def tree(folder):
    folder = pathlib.Path(folder)
    if not folder.exists():
        return []
    return sorted(str(p.relative_to(folder)) for p in folder.rglob("*"))


def env_for(data, bin_dir, **extra):
    home = data.root / "userhome"
    home.mkdir(exist_ok=True)
    path = [str(bin_dir), os.path.dirname(sys.executable)]
    if os.name == "nt":
        system = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
        path += [system, os.environ.get("SystemRoot", r"C:\Windows")]
    else:
        path += ["/usr/bin", "/bin"]
    env = base_env({"HOME": str(home), "USERPROFILE": str(home), "PATH": os.pathsep.join(path)})
    env.update({k: str(v) for k, v in extra.items()})
    return env


user = pathlib.Path(tempfile.mkdtemp(prefix="ffv-fake-user-"))
try:
    clip = user / "clip.mp4"
    clip.write_bytes(b"\x00" * 4096)

    # -----------------------------------------------------------------------------------------
    print("scenario: FFmpeg 5.1 is refused")
    with FakeDataDir() as data:
        home = data.install("ffmpeg-video")
        bin_dir = make_fake_bin(data.root / "fake")
        env = env_for(data, bin_dir, FAKE_FF_VERSION="5.1")
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.edit.cut", "input": str(clip), "output": "a.mp4",
                                                     "start": "1", "end": "2", "dry_run": True}, env=env)
        check("a tool call with ffmpeg 5.1: DEPENDENCY_MISSING", doc and doc.get("code") == "DEPENDENCY_MISSING", out[:400])
        check("... naming the version and an upgrade fix", doc and "5.1" in doc.get("error", "")
              and any(p.get("code") == "ffmpeg_too_old" and p.get("fix") for p in doc.get("problems") or []), out[:400])
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.setup.doctor"}, env=env)
        check("doctor with ffmpeg 5.1: DEPENDENCY_MISSING with ready false and the output root",
              doc and doc.get("code") == "DEPENDENCY_MISSING" and doc.get("doctor", {}).get("ready") is False
              and doc["doctor"].get("outputRoot"), out[:400])

    # -----------------------------------------------------------------------------------------
    print("scenario: dry runs with FFmpeg 7.1")
    with FakeDataDir() as data:
        home = data.install("ffmpeg-video")
        bin_dir = make_fake_bin(data.root / "fake")
        log = data.root / "ff.jsonl"
        env = env_for(data, bin_dir, FAKE_FF_VERSION="7.1", FAKE_FF_LOG=log)
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.setup.doctor"}, env=env)
        check("doctor: ready with the output root", doc and doc.get("ok") is True and doc.get("summary", {}).get("ready") is True
              and doc["result"].get("outputRoot"), out[:600])
        check("doctor: reports the fake binaries and the deadline",
              doc and str(bin_dir).lower() in str(doc["result"]["ffmpeg"]["path"]).lower()
              and doc["result"].get("deadlineSeconds") == 1740, out[:600])
        before = tree(data.output_root)
        calls = {
            "ffmpeg.edit.cut": {"input": str(clip), "output": "dry/cut.mp4", "start": "1", "end": "3"},
            "ffmpeg.adjust.fit": {"input": str(clip), "output": "dry/fit.mp4", "aspect": "9:16", "fit": "blur"},
            "ffmpeg.deliver.export": {"input": str(clip), "output": "dry/export.mp4", "preset": "youtube"},
        }
        for tool, args in calls.items():
            log.write_text("", encoding="utf-8")
            doc, out, err, rc = run_process(data, home, dict(args, tool=tool, dry_run=True), env=env)
            check(f"{tool} dry run succeeds", doc and doc.get("ok") is True and doc.get("dryRun") is True
                  and doc.get("outputs") == [], out[:500])
            ran = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
            encodes = [r for r in ran if r["name"] == "ffmpeg" and "-i" in r["argv"]]
            check(f"{tool} dry run never runs an ffmpeg encode", not encodes, encodes[:1])
        check("dry runs leave the output root unchanged", tree(data.output_root) == before,
              (before, tree(data.output_root)))
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.edit.cut", "input": str(clip), "output": "dry/cut.mp4",
                                                     "start": "1", "end": "3", "dry_run": True, "detail": "full"}, env=env)
        check("detail full returns the command lines", doc and doc.get("ok") and isinstance(doc["result"].get("commands"), list)
              and doc["result"]["commands"], out[:400])

    # -----------------------------------------------------------------------------------------
    print("scenario: a hanging ffmpeg under a 75 s sandbox limit")
    with FakeDataDir() as data:
        home = data.install("ffmpeg-video", patch_manifest=lambda m: m["sandbox"].update(timeoutSeconds=75))
        bin_dir = make_fake_bin(data.root / "fake")
        pidfile = data.root / "hang.pid"
        env = env_for(data, bin_dir, FAKE_FF_VERSION="7.1", FAKE_FF_HANG="1", FAKE_FF_PIDFILE=pidfile)
        out_dir = data.output_root / "hang"
        out_dir.mkdir(parents=True)
        old_lock = out_dir / ".older.mp4.ffskill-lock"
        old_lock.write_text("999999", encoding="utf-8")
        old_time = time.time() - 7200
        os.utime(old_lock, (old_time, old_time))
        started = time.time()
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.adjust.reverse", "input": str(clip),
                                                     "output": "hang/reversed.mp4"}, env=env, timeout=120)
        took = time.time() - started
        check("TIMEOUT is structured", doc and doc.get("ok") is False and doc.get("code") == "TIMEOUT"
              and doc.get("errorKind") == "timeout" and doc.get("hint"), out[:500])
        check("TIMEOUT returns well inside the 75 s limit", took < 45, round(took, 1))
        check("exit 0 and one JSON line", rc == 0 and len(out.strip().splitlines()) == 1)
        check("the fake really started an encode", pidfile.exists())
        pid = int(pidfile.read_text()) if pidfile.exists() else 0
        deadline = time.time() + 10
        while pid and pid_alive(pid) and time.time() < deadline:
            time.sleep(0.2)
        check("no fake ffmpeg process is left running", not pid_alive(pid), pid)
        left = tree(out_dir)
        check("no partial output", not (out_dir / "reversed.mp4").exists(), left)
        check("no lock or hidden sibling of this run", not [n for n in left if "reversed" in n], left)
        check("an older lock of another output is kept", old_lock.exists(), left)
        check("no per-call temp folder remains", not (data.output_root / ".tmp").exists()
              or not list((data.output_root / ".tmp").iterdir()), tree(data.output_root / ".tmp"))

    # -----------------------------------------------------------------------------------------
    print("scenario: what a failed run keeps, and the render cache")
    with FakeDataDir() as data:
        home = data.install("ffmpeg-video")
        bin_dir = make_fake_bin(data.root / "fake")
        env = env_for(data, bin_dir, FAKE_FF_VERSION="7.1")
        # the fake's 640x360 output fails a Reels check: upstream reports the render written and kept
        project = {"clips": [{"src": str(clip)}], "output": "checked/final.mp4", "check": {"platform": "reels"}}
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.project.render", "project_json": json.dumps(project)},
                                        env=env, timeout=300)
        final = data.output_root / "checked" / "final.mp4"
        check("a render whose check stage fails is TOOL_FAILED with upstream's verification kind",
              doc and doc.get("code") == "TOOL_FAILED"
              and ((doc.get("upstream") or {}).get("error") or {}).get("kind") == "verification", out[:600])
        check("... and the rendered file is kept on disk", final.is_file(), tree(data.output_root))
        check("... and named in the failure envelope as kept", doc and [os.path.normcase(p) for p in doc.get("kept") or []]
              == [os.path.normcase(str(final))], doc and doc.get("kept"))

        project = {"clips": [{"src": str(clip)}, {"src": str(clip)}], "output": "cached/final.mp4"}
        hits = []
        for _ in range(2):
            doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.project.render", "project_json": json.dumps(project),
                                                         "use_cache": True, "overwrite": True}, env=env, timeout=300)
            hits.append(((doc or {}).get("result") or {}).get("cache", {}).get("hits") if doc and doc.get("ok") else out[:300])
        check("use_cache: the second identical render reuses the finished join stage", hits[0] == [] and hits[1] == ["join"], hits)

    with FakeDataDir() as data:
        home = data.install("ffmpeg-video")
        bin_dir = make_fake_bin(data.root / "fake")
        # another call finishes the same output after this one resolved its paths: the fake's
        # -version run (the bridge's preflight) writes it, so upstream refuses with output_exists
        fake = bin_dir / "fake_ff.py"
        marker = '    if "-version" in ARGS or "--version" in ARGS:\n'
        source = fake.read_text(encoding="utf-8")
        check("the fake has the -version branch to hook", marker in source)
        fake.write_text(source.replace(marker, marker + (
            '        race = os.environ.get("FAKE_RACE_PATH")\n'
            '        if race and not os.path.exists(race):\n'
            '            with open(race, "wb") as fh:\n'
            '                fh.write(b"another call")\n'), 1), encoding="utf-8", newline="\n")
        target = data.output_root / "raced" / "final.mp4"
        env = env_for(data, bin_dir, FAKE_FF_VERSION="7.1", FAKE_RACE_PATH=target)
        doc, out, err, rc = run_process(data, home, {"tool": "ffmpeg.edit.cut", "input": str(clip), "output": "raced/final.mp4",
                                                     "start": "1", "end": "2"}, env=env)
        reason = (((doc or {}).get("upstream") or {}).get("error") or {}).get("reason")
        check("an output another call wrote meanwhile is refused (output_exists)", reason == "output_exists", out[:500])
        check("... and that call's file is left alone", target.is_file() and target.read_bytes() == b"another call",
              tree(data.output_root))
finally:
    shutil.rmtree(user, ignore_errors=True)

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
