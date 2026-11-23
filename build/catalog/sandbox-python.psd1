# Python import scan that Sophon runs on a skill entrypoint before every call (build/SkillLint.psm1,
# Test-SkillEntrypointImports).
#
# Mirrors sophon/src/Sophon.Sandbox/PythonImportResolver.cs at a431e1a64 (v2.2.2). Copy changes from that
# file; do not edit the lists by hand. How the resolver works (lines 17-41): when the manifest declares no
# requirements, the entrypoint text is split on LF, each line is TrimStart()ed, blank lines and lines
# starting with '#' are skipped, and ImportPattern is matched against what is left. Docstrings and string
# literals are NOT skipped. Every captured module that is not in StdlibModules is pip-installed (through
# ImportToPip when the names differ): on the process backend into the host Python, on Docker as
# 'pip install ... && python', so a failed install aborts the call.
@{
    SophonCommit  = 'a431e1a64'
    SophonVersion = '2.2.2'
    Source        = 'sophon/src/Sophon.Sandbox/PythonImportResolver.cs'

    # [GeneratedRegex(@"^(?:import|from)\s+(\w+)")], applied to each TrimStart()ed line (case-sensitive).
    ImportPattern = '^(?:import|from)\s+(\w+)'

    # SandboxedTool.cs:85-92 prepends this preamble to the entrypoint before it runs, so a __future__ import
    # is never the first statement and the script fails with SyntaxError. Always an error, whatever
    # requirements says.
    PreambleLines = @('import json, os', "params = json.loads(os.environ['SOPHON_PARAMS'])")
    ForbiddenModules = @('__future__')

    # StdlibModules (Python 3.13 top-level names, 205), in the source order. Ordinal comparison.
    StdlibModules = @(
        '__future__', '_thread',
        'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
        'atexit', 'audioop',
        'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins', 'bz2',
        'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
        'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
        'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
        'ctypes', 'curses',
        'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib', 'dis', 'distutils',
        'doctest',
        'email', 'encodings', 'enum', 'errno',
        'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'fractions',
        'ftplib', 'functools',
        'gc', 'getopt', 'getpass', 'gettext', 'glob', 'graphlib', 'grp', 'gzip',
        'hashlib', 'heapq', 'hmac', 'html', 'http',
        'idlelib', 'imaplib', 'imghdr', 'imp', 'importlib', 'inspect', 'io',
        'ipaddress', 'itertools',
        'json',
        'keyword',
        'lib2to3', 'linecache', 'locale', 'logging', 'lzma',
        'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder',
        'multiprocessing',
        'netrc', 'nis', 'nntplib', 'numbers',
        'operator', 'optparse', 'os', 'ossaudiodev',
        'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil', 'platform',
        'plistlib', 'poplib', 'posix', 'posixpath', 'pprint', 'profile', 'pstats',
        'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc',
        'queue', 'quopri',
        'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy',
        'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil',
        'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver',
        'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep',
        'struct', 'subprocess', 'sunau', 'symtable', 'sys', 'sysconfig', 'syslog',
        'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'test', 'textwrap',
        'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize', 'tomllib',
        'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types',
        'typing',
        'unicodedata', 'unittest', 'urllib', 'uu', 'uuid',
        'venv',
        'warnings', 'wave', 'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref',
        'xdrlib', 'xml', 'xmlrpc',
        'zipapp', 'zipfile', 'zipimport', 'zlib'
    )

    # ImportToPipMap: import name -> the pip package the resolver installs instead (used in messages only).
    ImportToPip = @{
        'bs4'         = 'beautifulsoup4'
        'cv2'         = 'opencv-python'
        'PIL'         = 'Pillow'
        'sklearn'     = 'scikit-learn'
        'yaml'        = 'pyyaml'
        'attr'        = 'attrs'
        'dateutil'    = 'python-dateutil'
        'dotenv'      = 'python-dotenv'
        'ffmpeg'      = 'ffmpeg-python'
        'gi'          = 'PyGObject'
        'serial'      = 'pyserial'
        'usb'         = 'pyusb'
        'wx'          = 'wxPython'
        'Crypto'      = 'pycryptodome'
        'jose'        = 'python-jose'
        'magic'       = 'python-magic'
        'docx'        = 'python-docx'
        'pptx'        = 'python-pptx'
        'Bio'         = 'biopython'
        'skimage'     = 'scikit-image'
        'gql'         = 'gql'
        'lxml'        = 'lxml'
        'psycopg2'    = 'psycopg2-binary'
        'mysql'       = 'mysql-connector-python'
        'readability' = 'readability-lxml'
    }
}
