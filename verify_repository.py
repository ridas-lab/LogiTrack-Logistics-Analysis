"""Verify the assembled repository's declared file hashes."""
from pathlib import Path
import hashlib, json
root=Path(__file__).resolve().parent
manifest=json.loads((root/'ASSEMBLY_MANIFEST.json').read_text())
for item in manifest['files']:
    path=root/item['path']
    assert path.is_file(), item['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'], item['path']
print(f"Verified {len(manifest['files'])} files against the assembly manifest.")
