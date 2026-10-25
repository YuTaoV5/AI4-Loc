"""Extract ordinary archives without imposing a log format. Keep opaque inputs intact."""
import gzip
import json
import pathlib
import shutil
import sys
import tarfile
import zipfile

LIMIT = 512 * 1024 * 1024
COUNT = 10000

def extract(source, destination):
    source, destination = pathlib.Path(source), pathlib.Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    used = 0
    count = 0

    def copy(name, stream):
        nonlocal used, count
        parts = pathlib.PurePosixPath(name.replace('\\', '/'))
        if parts.is_absolute() or '..' in parts.parts or ':' in name:
            raise ValueError('Archive path escapes problem directory')
        target = destination.joinpath(*parts.parts)
        count += 1
        if count > COUNT:
            raise ValueError('Archive exceeds file count limit')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            while chunk := stream.read(1024 * 1024):
                used += len(chunk)
                if used > LIMIT:
                    raise ValueError('Archive exceeds expanded size limit')
                output.write(chunk)

    try:
        if zipfile.is_zipfile(source):
            with zipfile.ZipFile(source) as archive:
                for item in archive.infolist():
                    if item.is_dir():
                        continue
                    if (item.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('Archive links are not extracted')
                    with archive.open(item) as stream:
                        copy(item.filename, stream)
        elif tarfile.is_tarfile(source):
            with tarfile.open(source) as archive:
                for item in archive:
                    if item.isdir():
                        continue
                    if not item.isfile():
                        raise ValueError('Archive links and special files are not extracted')
                    with archive.extractfile(item) as stream:
                        copy(item.name, stream)
        elif source.read_bytes()[:2] == b'\x1f\x8b':
            with gzip.open(source) as stream:
                copy('decompressed', stream)
        else:
            return {'status': 'opaque', 'message': '原始材料已保留，由 Skill 识别和处理。'}
        return {'status': 'extracted', 'files': count, 'bytes': used}
    except (ValueError, OSError, EOFError, RuntimeError, tarfile.TarError, zipfile.BadZipFile) as error:
        # No partial extraction is presented as complete. Original upload is never removed.
        shutil.rmtree(destination)
        destination.mkdir()
        return {'status': 'opaque', 'message': '保留原始文件，未展开：' + str(error)[:250]}

if __name__ == '__main__':
    print(json.dumps(extract(sys.argv[1], sys.argv[2]), ensure_ascii=False))
