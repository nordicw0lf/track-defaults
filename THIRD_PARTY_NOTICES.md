# Third-party notices

Track Defaults code and documentation are licensed under MIT. Bundled third-party software retains its own copyright notices and license terms.

## FFmpeg and FFprobe

The app invokes FFmpeg and FFprobe as separate command-line programs. The inspected Windows build is FFmpeg 9.0.2 essentials from Gyan, compiled with --enable-gpl and --enable-version3. These binaries are distributed under GPLv3 terms. The downloaded license text is retained in tools/LICENSE and included in ZIP packages as licenses/FFmpeg-GPLv3.txt.

Project and licensing information are available at https://ffmpeg.org/ and https://ffmpeg.org/legal.html. The binary supplier is https://www.gyan.dev/ffmpeg/builds/.

### Binary release requirements

Before publishing a package containing these binaries, provide access to the complete corresponding source for the exact build, including covered dependencies, patches, and build scripts, using a distribution method permitted by GPLv3 section 6. For downloads, provide clear source access instructions alongside the binaries and maintain the required availability. Preserve applicable copyright and license notices for the included dependencies.

The current packaging script includes the supplied GPL text but does not collect or verify complete corresponding FFmpeg source. General project homepage links do not establish that this requirement has been met. Existing downloadable releases need this source-availability review as well. Adding the app's MIT license does not resolve it.

The license text is available at https://www.gnu.org/licenses/gpl-3.0.html.

## Python and Tcl/Tk

Packaged executables include Python and Tcl/Tk. Their respective license and copyright notices must accompany redistribution. The ZIP builder copies the Python license and the Tcl/Tk license files from the Python installation used for the build.

Python licensing information is available at https://docs.python.org/3/license.html. Tcl/Tk licensing information is available at https://www.tcl.tk/software/tcltk/license.html.

## PyInstaller

The executable is built using PyInstaller. Its GPL license includes an exception allowing generated applications to use their own license. Preserve applicable notices when redistributing PyInstaller components. The licensing terms are available at https://pyinstaller.org/en/stable/license.html.
