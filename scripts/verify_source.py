from pathlib import Path
import json,hashlib,gzip
r=Path(__file__).resolve().parents[1]/'data/source';m=json.loads((r/'manifest.json').read_text())
name=m.get('normalized_file',m['stored_file']);expected=m.get('normalized_sha256',m['stored_sha256']);payload=(r/name).read_bytes()
assert hashlib.sha256(payload).hexdigest()==expected,'Pinned source checksum mismatch'
if not m.get('normalized_file'):assert hashlib.sha256(gzip.decompress(payload)).hexdigest()==m['original_sha256']
print('Pinned full-source integrity verified:',name)
