"""Media inspection and lossless default-track changes."""
from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parent
SUPPORTED = {'.mkv', '.mp4', '.m4v', '.mov'}
KEEP = 'Keep existing'
NONE = 'No default subtitle'
LANGUAGES = {'eng': 'English', 'en': 'English', 'heb': 'Hebrew', 'he': 'Hebrew',
             'jpn': 'Japanese', 'ja': 'Japanese', 'spa': 'Spanish', 'es': 'Spanish',
             'fra': 'French', 'fre': 'French', 'fr': 'French', 'deu': 'German',
             'ger': 'German', 'de': 'German', 'ara': 'Arabic', 'ar': 'Arabic',
             'rus': 'Russian', 'ru': 'Russian', 'ita': 'Italian', 'it': 'Italian',
             'por': 'Portuguese', 'pt': 'Portuguese', 'zho': 'Chinese',
             'chi': 'Chinese', 'zh': 'Chinese', 'kor': 'Korean', 'ko': 'Korean',
             'und': 'Unspecified'}

def tool(name):
    bundled = ROOT / 'tools' / (name + '.exe')
    found = str(bundled) if bundled.exists() else shutil.which(name)
    if not found:
        raise RuntimeError('Video tools are missing. Run setup_tools.py first.')
    return found

def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), **kwargs)

def inspect(path):
    result = run([tool('ffprobe'), '-v', 'error', '-show_streams', '-show_format',
                  '-show_chapters', '-of', 'json', str(path)], timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Could not read this video.')
    return json.loads(result.stdout)

def language(stream):
    code = stream.get('tags', {}).get('language', 'und').lower()
    return LANGUAGES.get(code, code)

def label(stream, ordinal):
    tags = stream.get('tags', {})
    parts = [f'{ordinal + 1}. {language(stream)}', tags.get('title', ''),
             stream.get('codec_name', '').upper()]
    if stream.get('channels'):
        parts.append(f"{stream['channels']} ch")
    flags = stream.get('disposition', {})
    if flags.get('default'):
        parts.append('current default')
    if flags.get('forced'):
        parts.append('forced')
    return ' · '.join(p for p in parts if p)

@dataclass
class Video:
    path: Path
    info: dict
    audio: object = KEEP
    subtitle: object = KEEP
    status: str = 'Ready'
    output: str = ''
    review: set = field(default_factory=set)

    def streams(self, kind):
        return [s for s in self.info['streams'] if s['codec_type'] == kind]

    def describe(self, kind):
        choice = self.audio if kind == 'audio' else self.subtitle
        if isinstance(choice, str):
            return choice
        for i, stream in enumerate(self.streams(kind)):
            if stream['index'] == choice:
                return label(stream, i)
        raise ValueError('Selected track no longer exists.')

def match_language(video, kind, wanted):
    matches = [s for s in video.streams(kind) if language(s) == wanted]
    if len(matches) != 1:
        raise ValueError('language missing' if not matches else 'multiple matching tracks; choose manually')
    return matches[0]['index']

def command_for(video, target):
    command = [tool('ffmpeg'), '-hide_banner', '-nostdin', '-v', 'error', '-n',
               '-i', str(video.path), '-map', '0', '-map_metadata', '0',
               '-map_chapters', '0', '-c', 'copy']
    for kind, choice in [('audio', video.audio), ('subtitle', video.subtitle)]:
        if choice == KEEP:
            continue
        streams = video.streams(kind)
        if choice != NONE and choice not in [s['index'] for s in streams]:
            raise ValueError('Selected track does not exist in this file.')
        for stream in streams:
            # Relative flag changes preserve forced, commentary, accessibility, etc.
            flag = '+default' if stream['index'] == choice else '-default'
            command += [f"-disposition:{stream['index']}", flag]
    if video.path.suffix.lower() == '.mkv':
        command += ['-default_mode', 'passthrough']
    return command + [str(target)]

def verify(video, output):
    actual = inspect(output)
    before = video.info['streams']
    after = actual['streams']
    if len(before) != len(after) or any(
            (a['codec_type'], a.get('codec_name')) != (b['codec_type'], b.get('codec_name'))
            for a, b in zip(before, after)):
        raise RuntimeError('Output verification failed: tracks were changed or lost.')
    for kind, choice in [('audio', video.audio), ('subtitle', video.subtitle)]:
        if choice == KEEP:
            continue
        for original, saved in zip(before, after):
            if original['codec_type'] == kind:
                expected = int(original['index'] == choice)
                if saved.get('disposition', {}).get('default', 0) != expected:
                    raise RuntimeError('This container did not retain the requested defaults. Try an MKV file.')

class Cancelled(Exception):
    pass

def save(video, directory, cancel):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(directory).free < video.path.stat().st_size * 1.02:
        raise RuntimeError('Not enough free space for a new copy of this video.')
    # Temporary data stays on the destination volume so publication is atomic.
    with tempfile.TemporaryDirectory(prefix='.track-defaults-', dir=directory) as temp:
        partial = Path(temp) / ('video' + video.path.suffix)
        with (Path(temp) / 'errors.txt').open('w+', encoding='utf-8') as log:
            process = subprocess.Popen(command_for(video, partial), stdout=subprocess.DEVNULL,
                                       stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            while process.poll() is None:
                if cancel.wait(0.15):
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    raise Cancelled()
            if process.returncode:
                log.seek(0)
                raise RuntimeError(log.read()[-4000:].strip() or 'Could not save this video.')
        if cancel.is_set():
            raise Cancelled()
        verify(video, partial)
        if cancel.is_set():
            raise Cancelled()
        index = 1
        while True:
            suffix = '' if index == 1 else f' ({index})'
            target = directory / f'{video.path.stem}.defaults{suffix}{video.path.suffix}'
            try:
                # Windows rename never overwrites an existing destination.
                if os.name == 'nt':
                    partial.rename(target)
                else:
                    os.link(partial, target)
                    partial.unlink()
                return target
            except FileExistsError:
                index += 1
