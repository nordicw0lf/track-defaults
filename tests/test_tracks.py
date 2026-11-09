from pathlib import Path
import tempfile
import threading
import unittest

from tracks import Video, KEEP, NONE, Cancelled, inspect, match_language, run, save, tool


class LanguageTests(unittest.TestCase):
    def test_matching_by_language_not_position(self):
        v = Video(Path('x.mkv'), {'streams': [
            {'index': 1, 'codec_type': 'audio', 'tags': {'language': 'jpn'}},
            {'index': 2, 'codec_type': 'audio', 'tags': {'language': 'eng'}}]})
        self.assertEqual(match_language(v, 'audio', 'English'), 2)
        with self.assertRaises(ValueError):
            match_language(v, 'audio', 'Hebrew')
        v.info['streams'].append({'index': 3, 'codec_type': 'audio', 'tags': {'language': 'en'}})
        with self.assertRaises(ValueError):
            match_language(v, 'audio', 'English')


class RemuxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            tool('ffmpeg')
            tool('ffprobe')
        except RuntimeError as exc:
            raise unittest.SkipTest(str(exc))
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        sub = cls.root / 'caption.srt'
        sub.write_text('1\n00:00:00,000 --> 00:00:01,000\nHello\n', encoding='utf-8')
        cls.source = cls.root / 'Original 日本語.mkv'
        command = [tool('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'color=s=160x90:d=1',
                   '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                   '-f', 'lavfi', '-i', 'sine=frequency=880:duration=1', '-i', str(sub),
                   '-map', '0:v', '-map', '1:a', '-map', '2:a', '-map', '3:s', '-map', '3:s',
                   '-c:v', 'mpeg4', '-c:a', 'aac', '-c:s', 'srt',
                   '-metadata:s:a:0', 'language=jpn', '-metadata:s:a:1', 'language=eng',
                   '-metadata:s:s:0', 'language=eng', '-metadata:s:s:1', 'language=heb',
                   '-disposition:a:0', 'default', '-disposition:a:1', '0',
                   '-disposition:s:0', 'default+forced', '-disposition:s:1', '0', str(cls.source)]
        result = run(command, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_defaults_streams_forced_and_no_overwrite(self):
        original = self.source.read_bytes()
        v = Video(self.source, inspect(self.source), audio=2, subtitle=4)
        out = save(v, self.root / 'output', threading.Event())
        info = inspect(out)['streams']
        self.assertEqual([s['disposition']['default'] for s in info], [0, 0, 1, 0, 1])
        self.assertEqual(info[3]['disposition']['forced'], 1)
        second = save(v, self.root / 'output', threading.Event())
        self.assertNotEqual(out, second)
        self.assertTrue(out.exists())
        self.assertEqual(original, self.source.read_bytes())

    def test_no_default_subtitle(self):
        v = Video(self.source, inspect(self.source), subtitle=NONE)
        result = inspect(save(v, self.root / 'none', threading.Event()))
        subs = [s for s in result['streams'] if s['codec_type'] == 'subtitle']
        self.assertTrue(all(s['disposition']['default'] == 0 for s in subs))

    def test_cancel_leaves_no_output(self):
        v = Video(self.source, inspect(self.source), audio=2)
        cancel = threading.Event()
        cancel.set()
        directory = self.root / 'cancelled'
        with self.assertRaises(Cancelled):
            save(v, directory, cancel)
        self.assertEqual(list(directory.iterdir()), [])

    def test_mp4_audio_default(self):
        path = self.root / 'test.mp4'
        result = run([tool('ffmpeg'), '-v', 'error', '-i', str(self.source),
                      '-map', '0:v', '-map', '0:a', '-c', 'copy', str(path)], timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        v = Video(path, inspect(path), audio=2)
        saved = inspect(save(v, self.root / 'mp4', threading.Event()))
        audio = [s for s in saved['streams'] if s['codec_type'] == 'audio']
        self.assertEqual([s['disposition']['default'] for s in audio], [0, 1])


if __name__ == '__main__':
    unittest.main()
