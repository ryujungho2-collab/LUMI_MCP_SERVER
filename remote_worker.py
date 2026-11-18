"""Isolated, size-limited worker for the remote MCP server."""
import base64
import binascii
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
os.environ['LUMI_ENGINE_DIR'] = str(ROOT / 'engine')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')


def main():
    request = json.load(sys.stdin)
    raw = base64.b64decode(request['video_base64'], validate=True)
    if not raw or len(raw) > 1024 * 1024:
        raise ValueError('Clip must be at most 1 MiB.')
    import cv2
    spec = importlib.util.spec_from_file_location('local_lumi_server', ROOT / 'local-pse' / 'server.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._engine()
    with tempfile.TemporaryDirectory(prefix='lumi-remote-') as temp:
        source = Path(temp) / 'clip.mp4'
        source.write_bytes(raw)
        cap = cv2.VideoCapture(str(source))
        try:
            if not cap.isOpened():
                raise ValueError('Unable to decode the MP4 clip.')
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
        finally:
            cap.release()
        if width <= 0 or height <= 0 or width * height > 320 * 240 or max(width, height) > 640:
            raise ValueError('Clip resolution must be at most 76,800 pixels (e.g. 320x240).')
        if not 0 < fps <= 60 or not 0 < frames <= 120:
            raise ValueError('Clip must have valid FPS <= 60 and 1–120 frames.')
        opts = {'l_max': request.get('l_max', 200.0), 'profile': request.get('profile', 'laptop'), 'device': 'cpu'}
        if request['action'] == 'analyze':
            result = module.analyze_video(str(source), **opts)
            result.pop('video', None)
        elif request['action'] == 'dim':
            out = Path(temp) / 'output.mp4'
            result = module.dim_partial_b2(str(source), str(out), mode=request.get('mode', 'base'), **opts)
            result.pop('output_video', None)
            output = out.read_bytes()
            if len(output) > 2 * 1024 * 1024:
                raise ValueError('Output exceeds the 2 MiB response limit.')
            result['output_mp4_base64'] = base64.b64encode(output).decode('ascii')
        else:
            raise ValueError('action must be analyze or dim')
        return result


if __name__ == '__main__':
    try:
        print(json.dumps(main(), ensure_ascii=False, allow_nan=False))
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        sys.exit(1)
