import os
import io
import zipfile
import hashlib
from typing import List, Tuple

TEXT_EXTS = {
	'.ts', '.tsx', '.js', '.jsx', '.json', '.md', '.html', '.css', '.scss', '.sass',
	'.py', '.java', '.cs', '.xml', '.yml', '.yaml', '.gradle', '.sh', '.bat', '.ps1', '.sql'
}

def _safe_name(name: str) -> str:
	return ''.join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in name)

def _hash_bytes(b: bytes) -> str:
	return hashlib.sha1(b).hexdigest()[:10]

def _iter_zip_text_files(zip_path: str) -> List[Tuple[str, bytes]]:
	files: List[Tuple[str, bytes]] = []
	with zipfile.ZipFile(zip_path, 'r') as zf:
		for zi in zf.infolist():
			if zi.is_dir():
				continue
			ext = os.path.splitext(zi.filename)[1].lower()
			if ext in TEXT_EXTS:
				data = zf.read(zi)
				files.append((zi.filename, data))
	return files

def _normalize_text(b: bytes) -> str:
	# best-effort decode
	for enc in ('utf-8', 'utf-16', 'latin-1'):
		try:
			return b.decode(enc)
		except Exception:
			continue
	return b.decode('utf-8', errors='ignore')

def prepare_code_from_zip(zip_path: str, project_name: str, project_code: str, out_dir: str) -> str:
	os.makedirs(out_dir, exist_ok=True)
	# destination folder structure like code_corpus_<name>/<project_name>/
	project_folder = os.path.join(out_dir, f"{_safe_name(project_name)}")
	os.makedirs(project_folder, exist_ok=True)

	entries = _iter_zip_text_files(zip_path)
	written = 0
	index_lines: List[str] = []
	for rel_path, data in entries:
		text = _normalize_text(data)
		# write a flattened file name: <rel>__1__<hash>.txt
		base = _safe_name(rel_path)
		digest = _hash_bytes(data)
		out_name = f"{base}__1__{digest}.txt"
		out_path = os.path.join(project_folder, out_name)
		with io.open(out_path, 'w', encoding='utf-8', newline='\n') as f:
			f.write(text)
		written += 1
		index_lines.append(f"{rel_path} -> {out_name}")

	# Write small manifest for traceability
	manifest_path = os.path.join(project_folder, 'code_corpus_manifest.txt')
	with io.open(manifest_path, 'w', encoding='utf-8') as mf:
		mf.write(f"project_name={project_name}\n")
		mf.write(f"project_code={project_code}\n")
		mf.write(f"source_zip={zip_path}\n")
		mf.write(f"files_written={written}\n")

	index_map_path = os.path.join(project_folder, 'file_map.txt')
	with io.open(index_map_path, 'w', encoding='utf-8') as idx:
		idx.write('\n'.join(index_lines))

	return project_folder
