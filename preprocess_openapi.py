#!/usr/bin/env python3
"""Preprocess an OpenAPI (Swagger) JSON file into semantically meaningful chunks.

Outputs:
  - ./openapi_chunks/<spec-stem>/chunks.jsonl : line-delimited JSON; each line is a chunk document
  - ./openapi_chunks/<spec-stem>/chunks/<id>.txt : human-readable chunk text (debugging / inspection)

Chunk Types:
  - global-info
  - operation
  - schema
  - enum
  - security (optional if securitySchemes present)

Simplifications (MVP):
  - No advanced splitting of very large operations or schemas yet.
  - Collect enum values from explicit enum arrays OR parse "Possible values:" in descriptions.
  - summary field is truncated to 180 chars.

Intended Use:
  1. Run this script to generate chunks from your OpenAPI file.
  2. Upload resulting per-chunk text (or push as docs) into the JSON vertical index.
  3. Later iterations can add operation splitting, examples extraction, version diffs, etc.

Example:
  python preprocess_openapi.py swaggerMAN.json
"""
from __future__ import annotations
import json
import re
import sys
import os
import hashlib
import argparse
from typing import Dict, Any, Iterable, List, Optional
from datetime import datetime, timezone

HTTP_METHODS = {"get","post","put","patch","delete","options","head"}

# --------------- Utility Functions ---------------

def load_spec(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def safe_id(s: str) -> str:
    """Return a filesystem-safe identifier (Windows compatible).

    Replaces characters that are invalid in Windows filenames (<>:"/\|?*) or
    could create nested paths (slashes, colons) with underscores, then collapses repeats.
    """
    # Replace path/namespace separators explicitly first
    s = s.replace(':', '_').replace('/', '_').replace('\\', '_')
    # Remove other forbidden characters
    s = re.sub(r'[<>:"\\/|?*]+', '_', s)
    # Collapse multiple underscores
    s = re.sub(r'_+', '_', s)
    return s.strip('_')[:160]

def first_sentence(text: str, max_len: int = 180) -> str:
    if not text:
        return ''
    txt = text.strip().replace('\n', ' ')
    # Sentence boundary heuristic
    m = re.search(r'([.!?])\s', txt)
    if m and m.start() > 40:  # reasonable first sentence length
        sent = txt[:m.end()].strip()
    else:
        sent = txt[:max_len]
    return sent[:max_len]

def approx_tokens(text: str) -> int:
    return int(len(text)/4)

def extract_schema_refs(obj: Any) -> List[str]:
    refs = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == '$ref' and isinstance(v, str) and v.startswith('#/components/schemas/'):
                refs.add(v.split('/')[-1])
            else:
                refs.update(extract_schema_refs(v))
    elif isinstance(obj, list):
        for item in obj:
            refs.update(extract_schema_refs(item))
    return sorted(refs)

def parse_enum_from_description(desc: str) -> List[str]:
    if not desc:
        return []
    # Look for 'Possible values:' or bullet list style
    m = re.search(r'Possible values:\s*(.*)', desc, flags=re.IGNORECASE)
    if not m:
        return []
    tail = m.group(1)
    # Split by commas or asterisks/newlines
    candidates = re.split(r'[*,\n]\s*', tail)
    values = []
    for c in candidates:
        c = c.strip().strip('.').strip(',')
        if not c:
            continue
        # stop if looks like a new sentence
        if len(c.split()) > 4:
            continue
        if len(c) > 30:
            continue
        values.append(c)
    # Deduplicate while preserving order
    seen = set()
    out = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out

# --------------- Chunk Builders ---------------

def build_operation_chunks(path: str, method: str, op: Dict[str, Any], version: str) -> Dict[str, Any]:
    op_id = f"op:{method}:{path}"
    tags = op.get('tags', [])
    summary_val = op.get('summary') or op.get('description') or ''
    description = op.get('description') or ''
    auth_req = bool(op.get('security')) or any('x-authorization-required' in (op.get(k, {}) if isinstance(op.get(k), dict) else {}) for k in op.keys())

    # Parameters table
    parameters = op.get('parameters', [])
    param_lines = ["| name | in | type | required | description |",
                   "|------|----|------|----------|-------------|"]
    for p in parameters:
        name = p.get('name','')
        loc = p.get('in','')
        required = str(p.get('required', False)).lower()
        schema = p.get('schema', {})
        ptype = schema.get('type', schema.get('$ref','')).split('/')[-1]
        desc = (p.get('description') or '').replace('\n',' ')
        if len(desc) > 120:
            desc = desc[:117] + '...'
        param_lines.append(f"| {name} | {loc} | {ptype} | {required} | {desc} |")
    parameters_table = '\n'.join(param_lines) if parameters else "(no parameters)"

    # Request body
    body_lines = []
    if 'requestBody' in op:
        rb = op['requestBody']
        req_desc = rb.get('description','')
        if rb.get('content'):
            for ctype, spec in rb['content'].items():
                schema = spec.get('schema', {})
                refs = extract_schema_refs(schema)
                body_lines.append(f"Content-Type: {ctype} schemaRefs: {', '.join(refs) if refs else 'n/a'}")
        if req_desc:
            body_lines.append(f"Description: {req_desc.strip()[:300]}")
    request_body_block = '\n'.join(body_lines) or "(no request body)"

    # Responses
    responses = op.get('responses', {})
    resp_lines = []
    status_codes = []
    for code, rdef in responses.items():
        status_codes.append(code)
        rdesc = (rdef.get('description') or '').strip().replace('\n',' ')
        if len(rdesc) > 160:
            rdesc = rdesc[:157] + '...'
        schema_refs = []
        if rdef.get('content'):
            for ctype, spec in rdef['content'].items():
                schema_refs.extend(extract_schema_refs(spec.get('schema', {})))
        combined_refs = sorted(set(schema_refs))
        if combined_refs:
            resp_lines.append(f"{code} – {rdesc} (schemas: {', '.join(combined_refs)})")
        else:
            resp_lines.append(f"{code} – {rdesc}")
    responses_block = '\n'.join(resp_lines) or "(no responses)"

    # Schema refs overall
    all_refs = sorted(set(extract_schema_refs(op)))

    text_parts = [
        f"# {method.upper()} {path}",
        f"Tags: {', '.join(tags) if tags else 'n/a'}",
        f"Authorization: {'required' if auth_req else 'not required'}",
        f"Summary: {summary_val.strip()[:300]}",
        "\nParameters:", parameters_table,
        "\nRequest Body:", request_body_block,
        "\nResponses:", responses_block,
        f"\nSchemas referenced: {', '.join(all_refs) if all_refs else 'none'}"
    ]
    text = '\n'.join(text_parts)
    chunk = {
        "id": op_id,
        "docType": "operation",
        "method": method.upper(),
        "path": path,
        "tagList": [t.lower() for t in tags],
        "authRequired": auth_req,
        "statusCodes": status_codes,
        "schemaRefs": all_refs,
        "version": version,
        "summary": first_sentence(summary_val),
        "text": text,
        "tokensApprox": approx_tokens(text)
    }
    return chunk

def build_schema_chunk(name: str, schema: Dict[str, Any], version: str) -> List[Dict[str, Any]]:
    desc = schema.get('description','')
    enum_values = schema.get('enum') or parse_enum_from_description(desc)
    chunk_type = 'enum' if enum_values else 'schema'

    required = schema.get('required', [])
    props = schema.get('properties', {}) if isinstance(schema.get('properties'), dict) else {}
    field_lines = ["| field | type | required | description |", "|-------|------|----------|-------------|"]
    for fname, fdef in props.items():
        ftype = fdef.get('type') or fdef.get('$ref','').split('/')[-1] or 'object'
        freq = 'yes' if fname in required else 'no'
        fdesc = (fdef.get('description') or '').replace('\n',' ')
        if len(fdesc) > 120:
            fdesc = fdesc[:117] + '...'
        field_lines.append(f"| {fname} | {ftype} | {freq} | {fdesc} |")
    fields_table = '\n'.join(field_lines) if props else "(no properties)"

    refs = extract_schema_refs(schema)
    text_parts = [
        f"# Schema: {name}",
        f"Type: {schema.get('type','object')}",
        f"Description: {desc.strip()[:500]}",
    ]
    if enum_values:
        text_parts.append("Enum Values: " + ', '.join(enum_values[:100]))
    text_parts.extend([
        f"Required fields: {', '.join(required) if required else 'none'}",
        "\nFields:", fields_table,
        f"\nReferenced Schemas: {', '.join(refs) if refs else 'none'}"
    ])
    text = '\n'.join(text_parts)

    chunk = {
        "id": f"{chunk_type}:{name}",
        "docType": chunk_type,
        "schemaName": name,
        "enumValues": enum_values if enum_values else None,
        "schemaRefs": refs,
        "version": version,
        "summary": first_sentence(desc) or (f"Enum {name}" if enum_values else f"Schema {name}"),
        "text": text,
        "tokensApprox": approx_tokens(text)
    }
    return [chunk]


def build_global_chunk(spec: Dict[str, Any]) -> Dict[str, Any]:
    info = spec.get('info', {})
    version = info.get('version','')
    title = info.get('title','')
    paths = spec.get('paths', {})
    schemas = spec.get('components', {}).get('schemas', {})
    summary = f"API {title} version {version} with {len(paths)} paths and {len(schemas)} schemas."
    text = f"# API Global Info\nTitle: {title}\nVersion: {version}\nPaths: {len(paths)}\nSchemas: {len(schemas)}\nGenerated: {datetime.now(timezone.utc).isoformat()}"
    return {
        "id": "global:info",
        "docType": "global-info",
        "version": version,
        "summary": summary,
        "text": text,
        "tokensApprox": approx_tokens(text)
    }


def build_security_chunk(spec: Dict[str, Any]) -> Dict[str, Any] | None:
    sec = spec.get('components', {}).get('securitySchemes')
    if not sec:
        return None
    lines = ["# Security Schemes"]
    for name, cfg in sec.items():
        typ = cfg.get('type')
        desc = (cfg.get('description') or '').strip().replace('\n',' ')
        if typ == 'oauth2':
            flows = cfg.get('flows', {})
            for flow_name, flow in flows.items():
                scopes = flow.get('scopes', {})
                scope_list = ', '.join(f"{k}:{v[:40]}" for k,v in scopes.items())
                lines.append(f"{name} ({typ}/{flow_name}) scopes: {scope_list}")
        else:
            lines.append(f"{name} ({typ}) {desc}")
    text = '\n'.join(lines)
    return {
        "id": "security:schemes",
        "docType": "security",
        "version": spec.get('info', {}).get('version',''),
        "summary": first_sentence(text),
        "text": text,
        "tokensApprox": approx_tokens(text)
    }

# --------------- Main Processing ---------------

def generate_chunks(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    version = spec.get('info', {}).get('version','')
    chunks: List[Dict[str, Any]] = []
    chunks.append(build_global_chunk(spec))

    # Operations
    for path, methods in spec.get('paths', {}).items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in HTTP_METHODS:
                continue
            if not isinstance(op, dict):
                continue
            chunks.append(build_operation_chunks(path, method.lower(), op, version))

    # Schemas
    schemas = spec.get('components', {}).get('schemas', {})
    for name, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        chunks.extend(build_schema_chunk(name, schema, version))

    # Security
    sec_chunk = build_security_chunk(spec)
    if sec_chunk:
        chunks.append(sec_chunk)

    return chunks


def write_outputs(chunks: List[Dict[str, Any]], spec_path: str, out_dir: Optional[str]=None) -> str:
    stem = os.path.splitext(os.path.basename(spec_path))[0]
    if out_dir:
        base_dir = os.path.join(out_dir, stem)
    else:
        base_dir = os.path.join('openapi_chunks', stem)
    chunk_dir = os.path.join(base_dir, 'chunks')
    os.makedirs(chunk_dir, exist_ok=True)

    jsonl_path = os.path.join(base_dir, 'chunks.jsonl')
    with open(jsonl_path, 'w', encoding='utf-8') as jf:
        for ch in chunks:
            jf.write(json.dumps({k:v for k,v in ch.items() if v is not None}, ensure_ascii=False) + '\n')

    for ch in chunks:
        txt_path = os.path.join(chunk_dir, safe_id(ch['id']) + '.txt')
        with open(txt_path, 'w', encoding='utf-8') as tf:
            tf.write(ch['text'])
    return jsonl_path


def parse_args(argv: List[str]):
    p = argparse.ArgumentParser(description="Preprocess an OpenAPI spec into semantic chunks.")
    p.add_argument('spec', help='Path to OpenAPI / Swagger JSON file')
    p.add_argument('--out-dir', '-o', help='Base output directory (default: ./openapi_chunks)')
    return p.parse_args(argv)

def main():
    args = parse_args(sys.argv[1:])
    spec_path = args.spec
    spec = load_spec(spec_path)
    chunks = generate_chunks(spec)
    out_path = write_outputs(chunks, spec_path, args.out_dir)
    print(f"Generated {len(chunks)} chunks -> {out_path}")

if __name__ == '__main__':
    main()
