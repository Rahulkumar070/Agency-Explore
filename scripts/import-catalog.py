"""Import an extracted upstream repository. No third-party dependencies.

Usage: python3 scripts/import-catalog.py /path/to/agency-agents-main
"""
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/private/tmp/agency-source/agency-agents-main')
divisions = json.loads((source / 'divisions.json').read_text())['divisions']
tools = json.loads((source / 'tools.json').read_text())['tools']
tag_words = ['React', 'Vue', 'Angular', 'Svelte', 'TypeScript', 'Python', 'Rust', 'WordPress', 'Drupal', 'Shopify', 'SEO', 'Accessibility', 'Performance', 'Security', 'Analytics', 'API', 'Database', 'Content', 'Research', 'Testing', 'Design', 'Marketing', 'Mobile', 'DevOps', 'AI', 'Unity', 'Unreal', 'Sales', 'Privacy', 'Finance', 'GIS']

def clean(s):
    return re.sub(r'[*`#]', '', s).strip()

def sections(text, pattern):
    lines, active = [], False
    for line in text.splitlines():
        if re.match(r'^##\s', line):
            active = bool(re.search(pattern, line, re.I))
        elif active and line.startswith('### '):
            lines.append(clean(line))
    return lines[:6]

agents = []
(ROOT / 'dist/agents').mkdir(exist_ok=True)
for division in divisions:
    for path in sorted((source / division).rglob('*.md')):
        text = path.read_text()
        fm = re.match(r'^---\s*\n(.*?)\n---', text, re.S)
        if not fm:
            continue
        meta = {}
        key = ''
        for line in fm.group(1).splitlines():
            match = re.match(r'^([\w-]+):\s*(.*)', line)
            if match:
                key, value = match.groups()
                meta[key] = '' if value in ('>', '|', '>-', '|-') else value.strip('"\'')
            elif line.startswith(' ') and key:
                meta[key] += ' ' + line.strip()
        if not meta.get('name'):
            continue
        name = meta['name'].strip()
        desc = meta.get('description', meta.get('vibe', '')).strip()
        tags = [t for t in tag_words if re.search(r'(?<!\w)' + re.escape(t) + r'(?!\w)', name+' '+desc+' '+text[:2500], re.I)][:7]
        warnings = []
        if re.search(r'\b(?:you remember|persistent memory|remember previous)\b', text, re.I):
            warnings.append('The source uses memory language. Memory across runs depends on your host and is not provided by this explorer.')
        refs = sorted(set(re.findall(r'(?:\./)?[\w/-]+\.sh\b', text)))
        missing = [r for r in refs if not (source / r).exists() and not (source / 'scripts' / r).exists()]
        if missing:
            warnings.append('Some script references are not bundled in the upstream repository: ' + ', '.join(missing[:4]) + '. Check your project before using them.')
        (ROOT / 'dist/agents' / (path.stem + '.md')).write_text(text)
        search = ' '.join(sorted(set(re.findall(r'[^\W_]+', clean(text).lower()))))
        agents.append(dict(id=path.stem, name=name, description=desc, vibe=meta.get('vibe', '').strip(), emoji=meta.get('emoji', '◇'), division=division, tags=tags, missions=sections(text, r'mission'), deliverables=sections(text, r'deliverable'), workflows=sections(text, r'workflow'), source=str(path.relative_to(source)), sourceHash=hashlib.sha256(text.encode()).hexdigest(), search=search, warnings=warnings, evaluation='Not evaluated'))

ids = {a['id'] for a in agents}
assert len(ids) == len(agents), 'Duplicate agent slugs'
runbooks = json.loads((source / 'strategy/runbooks.json').read_text())['runbooks']
for runbook in runbooks:
    runbook['content'] = (source / runbook['doc']).read_text()
    runbook['missing'] = [i for g in runbook['roster'] for i in g['agents'] if i not in ids]
revision = sys.argv[2] if len(sys.argv) > 2 else 'main'
if revision != 'main' and not re.fullmatch(r'[a-f0-9]{40}', revision):
    raise ValueError('Revision must be a full Git commit SHA')
payload = dict(agents=agents, divisions=divisions, tools=tools, runbooks=runbooks, revision=revision, importedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(), repository='https://github.com/msitarzewski/agency-agents', license='MIT')
(ROOT / 'dist/catalog.json').write_text(json.dumps(payload, ensure_ascii=False))
(ROOT / 'dist/UPSTREAM-LICENSE.txt').write_text((source / 'LICENSE').read_text())
print(json.dumps(dict(agents=len(agents), divisions=len(divisions), runbooks=len(runbooks), unresolvedRunbookReferences=sum(len(r['missing']) for r in runbooks))))
