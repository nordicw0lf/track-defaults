"""Exercise the shipped executable and its bundled video tools."""
from pathlib import Path
import json
import tempfile
import threading

from tracks import Video, inspect, run, save, tool


def check(report_path):
    report = Path(report_path).resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    result = {'ok': False}
    try:
        with tempfile.TemporaryDirectory(prefix='package-check-', dir=report.parent) as folder:
            root = Path(folder)
            source = root / 'sample.mkv'
            created = run([tool('ffmpeg'), '-hide_banner', '-v', 'error',
                           '-f', 'lavfi', '-i', 'color=s=160x90:d=1',
                           '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                           '-map', '0:v', '-map', '1:a', '-map', '1:a',
                           '-c:v', 'mpeg4', '-c:a', 'aac',
                           '-disposition:a:0', 'default', '-disposition:a:1', '0',
                           str(source)], timeout=60)
            if created.returncode:
                raise RuntimeError(created.stderr)
            video = Video(source, inspect(source), audio=2)
            output = save(video, root / 'saved', threading.Event())
            streams = inspect(output)['streams']
            assert [s['disposition']['default'] for s in streams if s['codec_type'] == 'audio'] == [0, 1]
            from app import App
            window = App()
            window.withdraw()
            window.update_idletasks()
            window.destroy()
            result = {'ok': True, 'checks': ['bundled FFmpeg', 'bundled FFprobe',
                      'generated video', 'changed audio default', 'verified output tracks', 'desktop UI startup']}
    except Exception as exc:
        result['error'] = str(exc)
    report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['ok'] else 1
