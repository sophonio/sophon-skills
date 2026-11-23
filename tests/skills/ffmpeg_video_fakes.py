"""Fake ffmpeg/ffprobe for the ffmpeg-video tests, generated at test time (nothing binary in the repo).

    from ffmpeg_video_fakes import make_fake_bin
    bin_dir = make_fake_bin(tmp)       # bin_dir/ffmpeg(.cmd) and bin_dir/ffprobe(.cmd)
    env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]

On Windows each shim is a `.cmd` file that runs FAKE_SOURCE (written next to it as fake_ff.py)
under the current Python; on POSIX each shim is FAKE_SOURCE itself as an executable script.
Behaviour comes from the environment of the call:

    FAKE_FF_VERSION   the release both report (default 7.1)
    FAKE_FF_HANG=1    an encoding ffmpeg run writes a few bytes to its output and then hangs
    FAKE_FF_PIDFILE   where a hanging run writes its pid
    FAKE_FF_LOG       append one JSON line per invocation (name and argv)

A hanging run closes its standard handles first and exits once its parent is gone, so a test
on Windows (where killing the .cmd shim leaves its Python child behind) is not left waiting on
a pipe or with a stray process.
"""
import os
import pathlib
import stat
import sys

FAKE_SOURCE = r'''
import json, os, sys, time

if len(sys.argv) > 1 and sys.argv[1] in ("ffmpeg", "ffprobe") and os.path.basename(sys.argv[0]).startswith("fake_ff"):
    NAME, ARGS = sys.argv[1], sys.argv[2:]
else:
    NAME, ARGS = os.path.splitext(os.path.basename(sys.argv[0]))[0], sys.argv[1:]
VERSION = os.environ.get("FAKE_FF_VERSION", "7.1")
MAJOR = int(VERSION.split(".")[0])

ENCODERS = ["libx264", "libx265", "aac", "libopus", "libvorbis", "libmp3lame", "libsvtav1", "libaom-av1", "prores_ks",
            "libvpx-vp9", "pcm_s16le", "png", "mjpeg", "gif", "ffv1", "dnxhd", "qtrle", "hap", "flac", "alac", "mpeg4",
            "srt", "mov_text", "ass", "webvtt", "rawvideo", "pcm_s24le"]
FILTERS = ["scale", "pad", "crop", "fps", "format", "setsar", "setpts", "asetpts", "concat", "trim", "atrim", "overlay",
           "drawtext", "subtitles", "ass", "loudnorm", "volume", "amix", "acrossfade", "xfade", "boxblur", "gblur",
           "hqdn3d", "cropdetect", "silencedetect", "zscale", "tonemap", "colorspace", "lut3d", "eq", "hflip", "vflip",
           "transpose", "rotate", "reverse", "areverse", "tpad", "apad", "loop", "aloop", "split", "asplit", "hstack",
           "vstack", "xstack", "showwaves", "showspectrum", "vidstabdetect", "vidstabtransform", "yadif", "bwdif",
           "nlmeans", "atempo", "afade", "fade", "sidechaincompress", "aresample", "anull", "null", "color",
           "anullsrc", "testsrc2", "sine", "ebur128", "astats", "aformat", "channelsplit", "pan", "amerge", "v360",
           "deshake", "select", "tile", "palettegen", "paletteuse", "geq", "alphamerge", "premultiply", "unsharp",
           "drawbox", "delogo", "scdet", "blackdetect", "freezedetect", "idet", "signalstats", "showinfo", "asendcmd",
           "sendcmd", "dynaudnorm", "highpass", "lowpass", "afftdn", "agate", "acompressor", "alimiter", "chromakey",
           "colorkey", "lut", "lutrgb", "lutyuv", "curves", "vignette", "minterpolate", "framerate", "tblend", "blend"]
MUXERS = ["mp4", "mov", "matroska", "webm", "mp3", "ipod", "wav", "adts", "flac", "ogg", "opus", "gif", "image2",
          "srt", "ass", "webvtt", "null", "segment", "hls", "ffmetadata", "apng", "mpegts"]


def version_text():
    major = VERSION.split(".")[0]
    avutil = {"5": 57, "6": 58, "7": 59, "8": 60}.get(major, 59)
    return (f"{NAME} version {VERSION} Copyright (c) 2000-2026 the FFmpeg developers\n"
            f"built with fake\nconfiguration: --enable-gpl --enable-libx264 --enable-libass --enable-libfreetype\n"
            f"libavutil      {avutil}. 10.100 / {avutil}. 10.100\n")


def listing(flag):
    if flag == "-encoders":
        rows = [(" V....D " if n not in ("aac", "libopus", "libvorbis", "libmp3lame", "pcm_s16le", "flac", "alac", "pcm_s24le")
                 else " A....D ") + f"{n:<20} fake {n}" for n in ENCODERS]
        return "Encoders:\n V..... = Video\n ------\n" + "\n".join(rows) + "\n"
    if flag == "-decoders":
        return "Decoders:\n V..... = Video\n ------\n" + "\n".join(f" V....D {n:<20} fake" for n in ENCODERS + ["h264", "hevc"]) + "\n"
    if flag == "-filters":
        return "Filters:\n  T.. = Timeline support\n" + "\n".join(f" ... {n:<20} V->V       fake {n}" for n in FILTERS) + "\n"
    if flag in ("-muxers", "-formats"):
        return "File formats:\n D. = Demuxing supported\n --\n" + "\n".join(f"  E {n:<15} fake" for n in MUXERS) + "\n"
    if flag == "-bsfs":
        return "Bitstream filters:\nh264_mp4toannexb\nhevc_mp4toannexb\naac_adtstoasc\nh264_metadata\nhevc_metadata\nav1_metadata\nfilter_units\nvp9_metadata\nmpeg2_metadata\n"
    if flag == "-pix_fmts":
        return "Pixel formats:\nIO... yuv420p 3 12 8-8-8\nIO... yuva420p 4 20 8-8-8-8\nIO... rgba 4 32 8-8-8-8\n"
    if flag == "-hwaccels":
        return "Hardware acceleration methods:\n\n"
    return ""


STREAMS = [
    {"index": 0, "codec_type": "video", "codec_name": "h264", "profile": "High", "codec_tag_string": "avc1",
     "width": 640, "height": 360, "coded_width": 640, "coded_height": 360, "pix_fmt": "yuv420p",
     "sample_aspect_ratio": "1:1", "display_aspect_ratio": "16:9", "r_frame_rate": "30/1", "avg_frame_rate": "30/1",
     "time_base": "1/15360", "start_time": "0.000000", "duration": "8.000000", "nb_frames": "240", "bit_rate": "500000",
     "color_range": "tv", "color_space": "bt709", "color_transfer": "bt709", "color_primaries": "bt709",
     "field_order": "progressive", "disposition": {"default": 1, "attached_pic": 0}, "tags": {"language": "und"}},
    {"index": 1, "codec_type": "audio", "codec_name": "aac", "profile": "LC", "codec_tag_string": "mp4a",
     "sample_rate": "48000", "channels": 2, "channel_layout": "stereo", "sample_fmt": "fltp", "time_base": "1/48000",
     "start_time": "0.000000", "duration": "8.000000", "bit_rate": "128000",
     "disposition": {"default": 1, "attached_pic": 0}, "tags": {"language": "und"}},
]


def probe_doc(target):
    return {"streams": STREAMS, "chapters": [],
            "format": {"filename": target, "nb_streams": 2, "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                       "format_long_name": "QuickTime / MOV", "start_time": "0.000000", "duration": "8.000000",
                       "size": str(os.path.getsize(target)) if os.path.exists(target) else "500000",
                       "bit_rate": "628000", "tags": {"major_brand": "isom"}}}


def ffprobe():
    target = ARGS[-1] if ARGS else ""
    wants_csv = any(a.startswith("csv") or a.startswith("default=") or a == "compact" for a in ARGS)
    entries = ""
    for i, a in enumerate(ARGS):
        if a == "-show_entries" and i + 1 < len(ARGS):
            entries = ARGS[i + 1]
    if wants_csv:
        if "codec_type" in entries:
            print("video\naudio")
        elif "start_time" in entries:
            print("0.000000")
        elif "duration" in entries:
            print("8.000000")
        elif "width" in entries or "height" in entries:
            print("640,360")
        return 0
    print(json.dumps(probe_doc(target)))
    return 0


def parent_alive(ppid):
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, ppid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    return os.getppid() == ppid


def hang(output):
    if output:
        try:
            with open(output, "wb") as fh:
                fh.write(b"\x00\x00\x00\x18ftypisom partial")
        except OSError:
            pass
    pidfile = os.environ.get("FAKE_FF_PIDFILE")
    if pidfile:
        with open(pidfile, "w") as fh:
            fh.write(str(os.getpid()))
    ppid = os.getppid()
    for fd in (0, 1, 2):
        try:
            os.close(fd)
        except OSError:
            pass
    deadline = time.time() + 120
    while time.time() < deadline and parent_alive(ppid):
        time.sleep(0.2)
    os._exit(0)


def ffmpeg():
    output = ARGS[-1] if ARGS and not ARGS[-1].startswith("-") else None
    if os.environ.get("FAKE_FF_HANG") == "1" and "-i" in ARGS:
        hang(output)
    if output and output not in ("-", "pipe:1") and "null" not in ARGS:
        with open(output, "wb") as fh:
            fh.write(b"fake")
    return 0


def main():
    log = os.environ.get("FAKE_FF_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"name": NAME, "argv": ARGS}) + "\n")
    if "-version" in ARGS or "--version" in ARGS:
        sys.stdout.write(version_text())
        return 0
    for flag in ("-encoders", "-decoders", "-filters", "-muxers", "-formats", "-bsfs", "-pix_fmts", "-hwaccels"):
        if flag in ARGS:
            sys.stdout.write(listing(flag))
            return 0
    return ffprobe() if NAME == "ffprobe" else ffmpeg()


sys.exit(main())
'''


def make_fake_bin(folder, python=None):
    """Write fake_ff.py plus ffmpeg/ffprobe shims into `folder`/bin and return that folder."""
    python = python or sys.executable
    bin_dir = pathlib.Path(folder) / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    source = bin_dir / "fake_ff.py"
    source.write_text(FAKE_SOURCE, encoding="utf-8", newline="\n")
    for name in ("ffmpeg", "ffprobe"):
        if os.name == "nt":
            shim = bin_dir / f"{name}.cmd"
            shim.write_text(f'@"{python}" -B "{source}" {name} %*\r\n', encoding="utf-8", newline="")
        else:
            # the fake itself, so a kill reaches it directly (no wrapper process in between)
            shim = bin_dir / name
            shebang = f"#!{python} -B" if " " not in python else "#!/usr/bin/env python3"
            shim.write_text(shebang + "\n" + FAKE_SOURCE, encoding="utf-8", newline="\n")
            shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def pid_alive(pid):
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        with open(f"/proc/{int(pid)}/stat") as fh:
            return fh.read().split()[2] != "Z"
    except OSError:
        return True
