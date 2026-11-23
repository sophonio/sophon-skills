"""ffmpeg-video against a real FFmpeg 6.1+ (lavfi fixtures; no media in the repo).

Not a test_* file, so run_all.py skips it; CI calls it directly on runners that install FFmpeg:

    python tests/skills/ffmpeg_video_media.py            # skips cleanly when ffmpeg/ffprobe are missing
    CI_REQUIRE_FFMPEG=1 python tests/skills/ffmpeg_video_media.py   # missing FFmpeg is a failure

Every call goes through the real Sophon shape (sandboxsim.run_process). Covers:
1. doctor reports ready and an output root;
2. a dry run of every tool from build/ffmpeg-video/smoke-args.json leaves the output root unchanged,
   and the non-dry smoke calls (verify, doctor, contract) succeed;
3. the chain probe -> insert -> background -> cut -> join -> caption -> audio -> render (9:16
   project_json with audio.replace and music together) -> check -> look -> export -> verify;
   the same render again hits the stage cache, and a 16:9 render checked for reels fails its
   check stage but keeps the finished file (named in `kept`);
4. a timeout gives a clean structured TIMEOUT with no partial output;
5. writing the same output twice is refused the second time (output_exists), and overwrite
   inside the output root then succeeds.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sandboxsim import REPO, FakeDataDir, base_env, run_process  # noqa: E402

SMOKE = json.loads((REPO / "build" / "ffmpeg-video" / "smoke-args.json").read_text(encoding="utf-8"))
REQUIRE = os.environ.get("CI_REQUIRE_FFMPEG") == "1"
IGNORED_IN_SNAPSHOT = (".tmp", ".cache")

ok = True


def check(name, cond, detail=""):
    global ok
    print(f"{'ok  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  -- {str(detail)[:900]}"))
    ok &= bool(cond)
    return bool(cond)


def snapshot(root):
    root = pathlib.Path(root)
    if not root.exists():
        return []
    found = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in IGNORED_IN_SNAPSHOT:
            continue
        found.append(str(rel))
    return sorted(found)


def ffmpeg(*args):
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"fixture ffmpeg {' '.join(args)} failed: {proc.stderr[-500:]}")


def make_fixtures(folder):
    folder = pathlib.Path(folder)
    video = folder / "fx.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=d=8:s=640x360:r=30", "-f", "lavfi", "-i", "sine=f=440:d=8:sample_rate=48000",
           "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2", str(video))
    video2 = folder / "fx2.mp4"
    shutil.copyfile(video, video2)
    image = folder / "still.png"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=640x360", "-frames:v", "1", str(image))
    audio = folder / "tone.wav"
    ffmpeg("-f", "lavfi", "-i", "sine=f=220:d=8:sample_rate=48000", "-ac", "2", str(audio))
    cues = folder / "cues.txt"
    cues.write_text("0:00-0:02 Hello\n0:02-0:04 World\n", encoding="utf-8")
    frames = folder / "frames"
    frames.mkdir()
    ffmpeg("-f", "lavfi", "-i", "testsrc2=d=1:s=640x360:r=30", str(frames / "frame_%04d.png"))
    for i, png in enumerate(sorted(frames.glob("frame_*.png"))):  # frame_0000 ... frame_0029, as smoke-args says
        png.rename(frames / f"frame_{i:04d}.png")
    clips = folder / "clips"
    clips.mkdir()
    for name in ("a.mp4", "b.mp4"):
        ffmpeg("-f", "lavfi", "-i", "testsrc2=d=2:s=640x360:r=30", "-f", "lavfi", "-i", "sine=d=2", "-shortest",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(clips / name))
    long_video = folder / "long.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=d=60:s=1280x720:r=30", "-f", "lavfi", "-i", "sine=d=60", "-shortest",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(long_video))
    return {"${video}": str(video), "${video2}": str(video2), "${image}": str(image), "${audio}": str(audio),
            "${cues}": str(cues), "${frames}": str(frames), "${clips}": str(clips), "long": str(long_video)}


def substitute(value, values):
    if isinstance(value, str):
        for key, text in values.items():
            value = value.replace(key, text)
        return value
    if isinstance(value, list):
        return [substitute(v, values) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, values) for k, v in value.items()}
    return value


def smoke_args(name, values):
    args = substitute(SMOKE["calls"][name]["args"], values)
    for key, value in list(args.items()):
        if key.endswith("_json") and isinstance(value, (dict, list)):
            args[key] = json.dumps(value)
    return args


def main():
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        if REQUIRE:
            check("ffmpeg and ffprobe are on PATH (CI_REQUIRE_FFMPEG=1)", False, os.environ.get("PATH"))
            return
        print("SKIP: ffmpeg/ffprobe not on PATH (set CI_REQUIRE_FFMPEG=1 to make this a failure)")
        return
    work = pathlib.Path(tempfile.mkdtemp(prefix="ffv-media-"))
    try:
        with FakeDataDir() as data:
            home = data.install("ffmpeg-video")
            userhome = data.root / "userhome"
            userhome.mkdir()
            env = base_env({"HOME": str(userhome), "USERPROFILE": str(userhome)})

            def run(tool, args, timeout=1900):
                doc, out, err, rc = run_process(data, home, dict(args, tool=tool), env=env, timeout=timeout)
                return doc or {"ok": False, "error": "no JSON", "stdout": out[-500:], "stderr": err[-500:]}

            values = make_fixtures(work)

            print("scenario: doctor")
            doc = run("ffmpeg.setup.doctor", {})
            root = (doc.get("result") or {}).get("outputRoot")
            check("doctor reports ready", doc.get("ok") is True and doc.get("summary", {}).get("ready") is True, doc)
            check("doctor reports the output root under documents/video/ffmpeg-video",
                  root and pathlib.Path(root) == data.output_root.resolve(), root)
            if not root:
                return
            values["${root}"] = root

            print("scenario: a dry run of every tool writes nothing")
            for name, call in SMOKE["calls"].items():
                args = smoke_args(name, values)
                before = snapshot(root)
                doc = run(name, args)
                if call.get("dryRun"):
                    check(f"{name} dry run", doc.get("ok") is True and doc.get("dryRun") is True, json.dumps(doc)[:900])
                    check(f"{name} dry run leaves the output root unchanged", snapshot(root) == before,
                          sorted(set(snapshot(root)) ^ set(before)))
                else:
                    check(f"{name} smoke call", doc.get("ok") is True, json.dumps(doc)[:900])

            print("scenario: the production chain")
            chain = {}

            def step(label, tool, args, key=None):
                doc = run(tool, args)
                out = doc.get("output") or (doc.get("outputs") or [None])[0]
                good = doc.get("ok") is True and (key is None or (out and os.path.isfile(out)))
                check(label, good, json.dumps(doc)[:900])
                if key:
                    chain[key] = out
                return doc

            doc = step("probe the source", "ffmpeg.inspect.probe", {"inputs": [values["${video}"]]})
            step("insert: still -> 3 s clip", "ffmpeg.make.insert",
                 {"input": values["${image}"], "output": "chain/still.mp4", "duration": "3"}, "still")
            step("background: 3 s gradient", "ffmpeg.make.background",
                 {"output": "chain/bg.mp4", "duration": "3", "width": 640, "height": 360}, "bg")
            step("cut 1-4 s", "ffmpeg.edit.cut", {"input": values["${video}"], "output": "chain/cut.mp4",
                                                  "start": "1", "end": "4"}, "cut")
            if chain.get("cut") and chain.get("still"):
                step("join cut + still", "ffmpeg.edit.join", {"inputs": [chain["cut"], chain["still"]],
                                                              "output": "chain/joined.mp4"}, "joined")
            if chain.get("joined"):
                step("caption from cue text", "ffmpeg.layer.caption", {"input": chain["joined"], "output": "chain/captioned.mp4",
                                                                        "text": values["${cues}"]}, "captioned")
            if chain.get("captioned"):
                step("audio: music bed, ducked", "ffmpeg.mix.audio", {"input": chain["captioned"], "output": "chain/mixed.mp4",
                                                                       "music": values["${audio}"], "duck": True}, "mixed")
            project = {"output": "chain/render.mp4",
                       "frame": {"aspect": "9:16", "width": 540, "height": 960, "fps": 30, "fit": "crop"},
                       "clips": [{"src": values["${video}"], "in": 0, "out": 2}, {"src": chain.get("still") or values["${video2}"]}],
                       "audio": {"replace": values["${audio}"], "music": values["${audio}"]}}
            started = time.time()
            step("render a 9:16 project_json (audio.replace and music together)", "ffmpeg.project.render",
                 {"project_json": json.dumps(project), "use_cache": True}, "render")
            print(f"      render took {time.time() - started:.1f} s")
            if chain.get("render"):
                again = run("ffmpeg.project.render", {"project_json": json.dumps(project), "use_cache": True, "overwrite": True})
                hits = ((again.get("result") or {}).get("cache") or {}).get("hits")
                check("the same render again reuses finished stages (use_cache)", again.get("ok") is True and hits,
                      json.dumps(again)[:900])
            wide = {"output": "chain/wide.mp4", "clips": [{"src": values["${video}"], "in": 0, "out": 2}],
                    "check": {"platform": "reels"}}
            doc = run("ffmpeg.project.render", {"project_json": json.dumps(wide)})
            kept = pathlib.Path(root) / "chain" / "wide.mp4"
            check("a 16:9 render checked for reels fails its check stage (verification)", doc.get("ok") is False and
                  ((doc.get("upstream") or {}).get("error") or {}).get("kind") == "verification", json.dumps(doc)[:900])
            check("... and the finished render is kept and named in `kept`", kept.is_file()
                  and [os.path.normcase(p) for p in doc.get("kept") or []] == [os.path.normcase(str(kept))], doc.get("kept"))
            if chain.get("render"):
                doc = step("check the render for reels", "ffmpeg.inspect.check", {"input": chain["render"], "platform": "reels"})
                step("look: contact sheet", "ffmpeg.inspect.look", {"input": chain["render"], "output": "chain/sheet.png",
                                                                    "tiles": "3x2"}, "sheet")
                step("export for reels", "ffmpeg.deliver.export", {"input": chain["render"], "output": "chain/export.mp4",
                                                                   "preset": "reels"}, "export")
            if chain.get("export"):
                step("verify the export (quick)", "ffmpeg.setup.verify", {"paths": [chain["export"]], "quick": True, "seconds": 3})

            print("scenario: timeout")
            doc = run("ffmpeg.edit.cut", {"input": values["long"], "output": "timeout/cut.mp4", "start": "0", "end": "59",
                                          "accurate": True, "preset": "veryslow", "timeout": 1})
            check("a 1 s timeout on a long encode gives TIMEOUT", doc.get("code") == "TIMEOUT", json.dumps(doc)[:600])
            check("... and leaves no partial output", not (pathlib.Path(root) / "timeout" / "cut.mp4").exists())

            print("scenario: overwrite")
            args = {"input": values["${video}"], "output": "ow/cut.mp4", "start": "0", "end": "1"}
            first = run("ffmpeg.edit.cut", args)
            second = run("ffmpeg.edit.cut", args)
            third = run("ffmpeg.edit.cut", dict(args, overwrite=True))
            check("the first write succeeds", first.get("ok") is True, json.dumps(first)[:400])
            check("the same output again is refused (output_exists)", second.get("ok") is False and
                  ((second.get("upstream") or {}).get("error") or {}).get("reason") == "output_exists", json.dumps(second)[:600])
            check("overwrite inside the output root succeeds", third.get("ok") is True, json.dumps(third)[:400])
            outside = work / "outside-root"
            outside.mkdir()
            env["FFMPEG_VIDEO_WRITE_ROOTS"] = str(outside)
            doc = run("ffmpeg.edit.cut", dict(args, output=str(outside / "x.mp4"), overwrite=True))
            check("overwrite outside the output root is refused", doc.get("code") == "PATH_NOT_ALLOWED", json.dumps(doc)[:400])
    finally:
        shutil.rmtree(work, ignore_errors=True)


main()
print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
