"""Build a portable Windows executable and a shareable ZIP."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / 'release'

def main():
    RELEASE.mkdir(exist_ok=True)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--onefile', '--windowed', '--name', 'Track Defaults',
                    '--distpath', str(RELEASE), '--workpath', str(ROOT / 'build'),
                    '--add-data', str(ROOT / 'tools') + ';tools',
                    '--add-data', str(ROOT / 'README.md') + ';.',
                    str(ROOT / 'app.py')], cwd=ROOT, check=True)
    exe = RELEASE / 'Track Defaults.exe'
    readme = RELEASE / 'START HERE.txt'
    readme.write_text(
        'TRACK DEFAULTS — Windows 10/11, 64-bit\n\n'
        'Extract this ZIP, then double-click Track Defaults.exe.\n'
        'No installation, Python, or administrator access is required.\n'
        'The first launch can take a few seconds while the included tools unpack.\n\n'
        '1. Add videos or a folder.\n'
        '2. Choose default audio/subtitle tracks per video, or apply languages to a batch.\n'
        '3. Check Save copies to, then click Save all planned changes.\n\n'
        'Originals remain unchanged. New copies need roughly the same disk space.\n'
        'Supported: MKV, MP4, M4V, MOV. Player language settings may override defaults.\n'
        'The app runs locally and does not upload videos.\n\n'
        'This release is unsigned.\n'
        'Video tools: FFmpeg essentials from https://www.gyan.dev/ffmpeg/builds/\n'
        'FFmpeg project and source: https://ffmpeg.org/\n'
        'See licenses and source folders for included notices and app source.\n', encoding='utf-8')
    archive = RELEASE / 'Track Defaults-Windows-x64.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for file in [exe, readme, ROOT / 'README.md']:
            bundle.write(file, 'Track Defaults/' + file.name)
        bundle.write(ROOT / 'tools' / 'LICENSE', 'Track Defaults/licenses/FFmpeg-GPLv3.txt')
        for file in ['app.py', 'tracks.py', 'setup_tools.py', 'package_check.py', 'build_release.py', 'requirements-build.txt', 'README.md']:
            bundle.write(ROOT / file, 'Track Defaults/source/' + file)
        python_license = Path(sys.base_prefix) / 'LICENSE.txt'
        if python_license.exists():
            bundle.write(python_license, 'Track Defaults/licenses/Python.txt')
        for file in (Path(sys.base_prefix) / 'tcl').rglob('license*'):
            if file.is_file():
                bundle.write(file, 'Track Defaults/licenses/' + str(file.relative_to(Path(sys.base_prefix) / 'tcl')))
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [exe, archive]}
    (RELEASE / 'SHA256.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    print(f'Ready: {archive} ({archive.stat().st_size / 1024 / 1024:.1f} MB)')

if __name__ == '__main__':
    main()
