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
            window.update_idletasks()
            save_controls = [window.out_entry] + [
                button for button in window.controls
                if button.cget('text') in ('Browse…', 'Save all planned changes')]
            for size in ('1180x760', '960x650'):
                window.geometry(size)
                window.update()
                for control in save_controls:
                    x = control.winfo_rootx() - window.winfo_rootx()
                    y = control.winfo_rooty() - window.winfo_rooty()
                    assert control.winfo_ismapped(), (size, str(control))
                    assert 0 <= x and x + control.winfo_width() <= window.winfo_width()
                    assert 0 <= y and y + control.winfo_height() <= window.winfo_height()
                    assert control.winfo_height() >= control.winfo_reqheight()
            window.withdraw()
            clear_button = next(button for button in window.controls
                                if button.cget('text') == 'Clear all videos')
            for selected in (True, False):
                for _ in range(3):
                    key = window.tree.insert('', 'end')
                    window.videos[key] = video
                    window.refresh(key)
                if selected:
                    window.tree.selection_set(key)
                window.select()
                window.batch_audio.configure(values=['Keep existing', 'English'])
                window.batch_audio.set('English')
                window.set_busy(True)
                clear_button.invoke()
                assert len(window.videos) == 3
                window.set_busy(False)
                clear_button.invoke()
                assert not window.videos and not window.tree.get_children()
                assert window.active is None
                assert window.audio.get() == window.subtitle.get() == ''
                assert window.batch_audio.get() == 'Keep existing'
                assert tuple(window.batch_audio['values']) == ('Keep existing',)
                assert window.batch_subtitle.get() == 'Keep existing'
                clear_button.invoke()
            selected_button = next(button for button in window.controls
                                   if button.cget('text') == 'Clear selected')
            keys = []
            for _ in range(4):
                key = window.tree.insert('', 'end')
                keys.append(key)
                window.videos[key] = Video(video.path, video.info, audio=2)
                window.refresh(key)
            selected_button.invoke()
            assert len(window.videos) == 4
            window.tree.selection_set(keys[0], keys[2])
            window.select()
            window.set_busy(True)
            selected_button.invoke()
            assert len(window.videos) == 4
            window.set_busy(False)
            selected_button.invoke()
            assert list(window.videos) == [keys[1], keys[3]]
            assert window.tree.get_children() == (keys[1], keys[3])
            assert all(v.audio == 2 for v in window.videos.values())
            assert window.active is None
            window.tree.selection_set(keys[1])
            selected_button.invoke()
            assert list(window.videos) == [keys[3]]
            window.tree.selection_set(keys[3])
            selected_button.invoke()
            assert not window.videos and not window.tree.get_children()
            assert window.audio.get() == window.subtitle.get() == ''
            assert tuple(window.batch_audio['values']) == ('Keep existing',)
            assert video.path.exists()
            window.destroy()
            result = {'ok': True, 'checks': ['bundled FFmpeg', 'bundled FFprobe',
                      'generated video', 'changed audio default', 'verified output tracks', 'desktop UI startup', 'save controls visible at startup and minimum size', 'clear all videos with one or no selection', 'clear disabled while busy', 'clear selected single and multiple rows', 'clear selected without selection', 'remaining video choices preserved']}
    except Exception as exc:
        result['error'] = str(exc)
    report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['ok'] else 1

