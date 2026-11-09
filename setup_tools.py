"""Download the Windows FFmpeg essentials build and verify its published checksum."""
from pathlib import Path
import hashlib
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
URL = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'

def install():
    target = ROOT / 'tools'
    target.mkdir(exist_ok=True)
    archive = target / 'ffmpeg.zip'
    print('Downloading video tools...', flush=True)
    urllib.request.urlretrieve(URL, archive)
    expected = urllib.request.urlopen(URL + '.sha256', timeout=60).read().decode().split()[0]
    actual = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    if actual.lower() != expected.lower():
        raise RuntimeError('Download checksum did not match. Please retry.')
    with zipfile.ZipFile(archive) as bundle:
        for name in bundle.namelist():
            leaf = Path(name).name
            if leaf in ('ffmpeg.exe', 'ffprobe.exe', 'LICENSE', 'LICENSE.txt'):
                (target / leaf).write_bytes(bundle.read(name))
    archive.unlink()
    print('Video tools are ready.', flush=True)

if __name__ == '__main__':
    install()
