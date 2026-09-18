"""端到端自测：真实启动 uvicorn，跑通 上传→分析→配乐→自动成片→渲染→导出。

用法：.venv/bin/python scripts/e2e.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import httpx

BASE = "http://localhost:8600"
ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ROOT / "data" / "music"
OUT = ROOT / "data" / "renders"

VARIANTS = [
    # (名字, ffmpeg 滤镜, 时长) —— 三种画风，便于场景/情绪有区分
    ("明亮_白天.mp4", "testsrc2=size=1280x720:rate=30,hue=b=20", 14),
    ("暗调_夜晚.mp4", "testsrc2=size=1920x1080:rate=30,negate", 11),
    ("高动态_街头.mp4", "testsrc2=size=1280x720:rate=30,rotate=4*sin(2*t)", 9),
]


def make_video(name: str, vf: str, seconds: int) -> Path:
    p = Path("/tmp") / name
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", vf,
         "-f", "lavfi", "-i", f"sine=frequency=330:duration={seconds}",
         "-t", str(seconds),
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-c:a", "aac",
         str(p)], check=True)
    return p


def make_music(name: str, seconds: int) -> Path:
    p = MUSIC_DIR / name
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}",
         "-af", f"tremolo=f=1.4:d=0.8,volume=0.8", "-c:a", "aac", str(p)], check=True)
    return p


def wait_job(c: httpx.Client, job_id: str, timeout_s: int = 300) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        j = c.get(f"{BASE}/renders/{job_id}").json()
        if j["status"] in ("done", "error", "cancelled"):
            return j
        time.sleep(1)
    raise TimeoutError(job_id)


def main() -> int:
    subprocess.run(["pkill", "-f", "uvicorn app.main"], capture_output=True)
    time.sleep(1)
    server = subprocess.Popen(
        [str(ROOT / ".venv" / "bin" / "uvicorn"), "app.main:app", "--port", "8600"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    try:
        c = httpx.Client(timeout=600)
        assert c.get(f"{BASE}/health").json()["status"] == "ok"

        print("== 1. 上传 3 段素材 ==")
        pid = None
        for name, vf, sec in VARIANTS:
            v = make_video(name, vf, sec)
            r = c.post(f"{BASE}/upload",
                       files={"file": (name, v.open("rb"), "video/mp4")},
                       data={"title": "E2E 测试项目"} if pid is None else {"projectId": str(pid)})
            r.raise_for_status()
            pid = pid or r.json()["projectId"]
        while True:
            assets = c.get(f"{BASE}/projects/{pid}").json()["assets"]
            if all(a["probeStatus"] == 1 and a["proxyStatus"] == 1 for a in assets):
                break
            time.sleep(1)
        print(f"   项目 {pid}：{len(assets)} 段全部解析+代理完成")

        print("== 2. AI 分析 ==")
        job = c.post(f"{BASE}/projects/{pid}/analysis").json()
        job = wait_job(c, job["jobId"])
        assert job["status"] == "done", job
        rep = c.get(f"{BASE}/projects/{pid}/analysis").json()["report"]
        print(f"   情绪构成 {rep['moodMix']} · BPM {rep['tempoBpm']} · {rep['meta']['paceAdvice']}")

        print("== 3. 配乐候选 ==")
        make_music("夜色公路.m4a", 45)
        make_music("城市清晨.m4a", 40)
        cands = c.get(f"{BASE}/projects/{pid}/music").json()["candidates"]
        assert cands, "配乐候选为空"
        print("   " + " | ".join(f"{m['title']} {m['match']}%" for m in cands))

        print("== 4. 自动成片（含渲染）==")
        r = c.post(f"{BASE}/projects/{pid}/auto-cut", json={
            "seed": 7, "musicId": cands[0]["musicId"],
            "preference": {"duration": "fit", "aspect": "9:16", "transitionStyle": "gentle"},
            "height": 1080, "fps": 30}).json()
        job = wait_job(c, r["jobId"])
        assert job["status"] == "done", job
        print(f"   渲染完成 v{job['result']['version']} · {job['result']['resolution']} · 用时 {job['result']['elapsedMs']/1000:.1f}s")
        print(f"   成片: {job['result']['url']}")

        print("== 5. 校验成片 ==")
        out = OUT / job["result"]["fileKey"]
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(out)],
            capture_output=True, text=True, check=True)
        import json as J
        info = J.loads(probe.stdout)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        dur = float(info["format"]["duration"])
        print(f"   {v['width']}x{v['height']} @{v['avg_frame_rate']} · {dur:.1f}s · {out.stat().st_size/1e6:.1f}MB")
        assert (v["width"], v["height"]) == (1080, 1920)
        exports = c.get(f"{BASE}/projects/{pid}/exports").json()["exports"]
        assert exports[0]["version"] == 1

        print("== 6. 换个剪法（新 seed 再出一版）==")
        r2 = c.post(f"{BASE}/projects/{pid}/auto-cut", json={
            "seed": 99, "musicId": cands[0]["musicId"],
            "preference": {"duration": "45s", "aspect": "9:16", "transitionStyle": "dynamic"},
            "height": 720, "fps": 30}).json()
        job2 = wait_job(c, r2["jobId"])
        assert job2["status"] == "done", job2
        exports = c.get(f"{BASE}/projects/{pid}/exports").json()["exports"]
        assert len(exports) == 2, "v1/v2 都应保留（不覆盖）"
        print(f"   v2 完成 · 720P · exports 共 {len(exports)} 版")
        print("\n✅ E2E 全链路通过")
        return 0
    finally:
        subprocess.run(["pkill", "-f", "uvicorn app.main"], capture_output=True)


if __name__ == "__main__":
    sys.exit(main())
