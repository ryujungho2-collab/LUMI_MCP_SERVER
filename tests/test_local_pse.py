import importlib.util
from pathlib import Path


def load_local():
    path = Path(__file__).resolve().parents[1] / "local-pse" / "server.py"
    spec = importlib.util.spec_from_file_location("lumi_local_for_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analyze_uses_b2_enhanced_config(monkeypatch, tmp_path):
    module = load_local()
    source = tmp_path / "input.mp4"
    source.write_bytes(b"dummy")
    seen = {}

    class B2Config:
        def to_mask_config(self):
            return {"enhanced_spatial_pattern": True}

    def analyze(path, **kwargs):
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(module, "_engine", lambda: (None, analyze, B2Config, None))
    monkeypatch.setattr(module, "_viewing", lambda *args: "view")
    monkeypatch.setattr(module, "_summary", lambda _: {})
    result = module.analyze_video(str(source))
    assert seen["mask_config"]["enhanced_spatial_pattern"] is True
    assert result["detector"] == "partial_b2_enhanced"
