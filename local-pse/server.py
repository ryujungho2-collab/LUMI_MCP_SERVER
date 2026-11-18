from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("LUMI PSE")
NOTICE = ("Experimental rule-based estimate; not a medical device or a guarantee of safety. "
          "Luminance assumes SDR/sRGB and a configured display white level; HDR is not supported.")


def _engine():
    root = os.environ.get("LUMI_ENGINE_DIR")
    if not root:
        raise ValueError("Set LUMI_ENGINE_DIR to the lumi-lab-rockrovks repository root.")
    engine = Path(root).expanduser().resolve() / "Fullscreen" / "A1"
    if not (engine / "vdcorefs" / "pipeline.py").is_file():
        raise ValueError(f"LUMI_ENGINE_DIR does not contain Fullscreen/A1/vdcorefs: {root}")
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    from vdcorefs import ViewingConfig, analyze_video
    from fullscreen_coreops_1112 import A1Config, dim_video_fullscreen_a1
    return ViewingConfig, analyze_video, A1Config, dim_video_fullscreen_a1


def _viewing(profile: str, l_max: float, diagonal_inch: float | None, distance_cm: float | None):
    if profile not in ("laptop", "desktop", "tv"):
        raise ValueError("profile must be laptop, desktop, or tv")
    for name, val in (("l_max", l_max), ("diagonal_inch", diagonal_inch), ("distance_cm", distance_cm)):
        if val is not None and (not isinstance(val, (int, float)) or not 0 < val < 10000):
            raise ValueError(f"{name} must be a positive finite value below 10000")
    ViewingConfig, _, _, _ = _engine()
    return ViewingConfig(profile=profile, l_max_cd_m2=l_max, diagonal_inch=diagonal_inch,
                         viewing_distance_cm=distance_cm)


def _summary(res):
    records = [{"label": r.label, "start_frame": int(r.start_frame), "end_frame": int(r.end_frame),
                "start_sec": float(r.start_sec), "end_sec": float(r.end_sec),
                "duration_sec": float(r.duration_sec), "peak_risk_calibrated": float(r.peak_risk_calibrated),
                "peak_risk_ppr_pct": float(r.peak_risk_ppr_pct), "peak_risk_nomura": float(r.peak_risk_nomura),
                "peak_risk_vfm_weibull": float(r.peak_risk_vfm_weibull)} for r in res.intervals]
    return {"is_dangerous": bool(res.is_dangerous), "labels": list(res.active_labels),
            "fps": float(res.fps), "frames": int(res.total_frames),
            "input_size": [int(res.orig_width), int(res.orig_height)],
            "analysis_size": [int(res.analysis_width), int(res.analysis_height)],
            "interval_count": len(records), "intervals": records[:100], "intervals_truncated": len(records) > 100}


def _input(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ValueError(f"Input video does not exist: {p}")
    return p


@mcp.tool()
def analyze_video(video_path: str, l_max: float = 200.0,
                  profile: Literal["laptop", "desktop", "tv"] = "laptop",
                  diagonal_inch: float | None = None, distance_cm: float | None = None,
                  device: Literal["cpu", "cuda"] = "cpu") -> dict:
    """Analyze a local SDR video for rule-based PSE hazard intervals. l_max is assumed SDR white in cd/m²."""
    p = _input(video_path)
    view = _viewing(profile, l_max, diagonal_inch, distance_cm)
    _, analyze, _, _ = _engine()
    result = analyze(p, viewing=view, device=device)
    return {"notice": NOTICE, "video": str(p), "assumed_l_max_cd_m2": l_max,
            "profile": profile, "result": _summary(result)}


@mcp.tool()
def dim_fullscreen_a1(video_path: str, output_path: str, l_max: float = 200.0,
                      mode: Literal["base", "hold", "safe"] = "base",
                      profile: Literal["laptop", "desktop", "tv"] = "laptop",
                      diagonal_inch: float | None = None, distance_cm: float | None = None,
                      device: Literal["cpu", "cuda"] = "cpu") -> dict:
    """Create a new A1 full-screen dimmed MP4 and separately analyze the encoded output. Audio is not retained."""
    source = _input(video_path)
    dest = Path(output_path).expanduser().resolve()
    if dest == source or dest.exists():
        raise ValueError("Output must be a new path; existing files are never overwritten.")
    if dest.suffix.lower() != ".mp4":
        raise ValueError("output_path must end in .mp4")
    view = _viewing(profile, l_max, diagonal_inch, distance_cm)
    _, analyze, A1Config, dim = _engine()
    result = dim(source, dest, a1_config=A1Config(mode=mode), viewing=view, device=device)
    encoded = analyze(dest, viewing=view, device=device)
    return {"notice": NOTICE, "output_video": str(dest), "audio_preserved": False,
            "assumed_l_max_cd_m2": l_max, "mode": mode,
            "before": _summary(result.before), "before_encoding": _summary(result.after),
            "encoded_output": _summary(encoded)}


if __name__ == "__main__":
    _engine()
    mcp.run(transport="stdio")


