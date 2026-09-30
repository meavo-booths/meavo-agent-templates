#!/usr/bin/env python3
"""Install portable workspace/Claude guidance without replacing project instructions."""
import argparse
from pathlib import Path
import re
import sys

TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'
BEGIN = '<!-- BEGIN WORKSPACE LAYOUT -->'
END = '<!-- END WORKSPACE LAYOUT -->'
RELEASE_BEGIN = '<!-- BEGIN MEAVO RELEASE POLICY -->'
RELEASE_END = '<!-- END MEAVO RELEASE POLICY -->'
FILES = ('AGENT_ENVIRONMENTS.md', '.cursor/rules/workspace-layout.mdc')


def checked_path(root, name):
    path = root / name
    current = path
    while current != root:
        if current.is_symlink():
            raise ValueError(f'Refusing symlink destination: {name}')
        current = current.parent
    if path.exists() and not path.is_file():
        raise ValueError(f'Destination is not a regular file: {name}')
    return path


def remove_block(text):
    if BEGIN not in text and END not in text:
        return text
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError('Missing or duplicate workspace block marker')
    start, finish = text.index(BEGIN), text.index(END)
    if finish < start:
        raise ValueError('Reversed workspace block markers')
    # A layout block may have been prepended by the local migration helper.
    # Preserve the rest of the document, including release-policy block bytes.
    return text[:start] + text[finish + len(END):].lstrip('\r\n')


def has_import(text):
    fence = None
    for line in text.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        elif fence is None and line.strip() == '@AGENTS.md':
            return True
    return False


def claude_document(text):
    # Release verifiers require their managed block first. Move only the
    # migration's import prefix; keep every custom note and release rule.
    if text.startswith('@AGENTS.md') and text[len('@AGENTS.md'):].lstrip('\r\n').startswith(RELEASE_BEGIN):
        text = text[len('@AGENTS.md'):].lstrip('\r\n')
    if not has_import(text):
        text = text.rstrip('\r\n') + ('\n\n' if text else '') + '@AGENTS.md\n'
    return text


def expected_files(target):
    contents = {}
    for name in ('AGENTS.md', 'CLAUDE.md', *FILES):
        checked_path(target, name)
    agents = target / 'AGENTS.md'
    existing = agents.read_bytes().decode() if agents.exists() else ''
    remaining = remove_block(existing)
    block = (TEMPLATES / 'AGENTS.workspace.md.template').read_text().rstrip('\n')
    if remaining.startswith(RELEASE_BEGIN) and RELEASE_END in remaining:
        end = remaining.index(RELEASE_END) + len(RELEASE_END)
        prefix, tail = remaining[:end], remaining[end:].lstrip('\r\n')
        document = prefix + '\n\n' + block + '\n' + ('\n' + tail if tail else '')
    else:
        document = block + '\n' + ('\n' + remaining if remaining else '')
    contents['AGENTS.md'] = document.encode()
    claude = target / 'CLAUDE.md'
    contents['CLAUDE.md'] = claude_document(claude.read_bytes().decode() if claude.exists() else '').encode()
    for name in FILES:
        contents[name] = (TEMPLATES / (name + '.template')).read_bytes()
    return contents


def sync(target, check=False):
    contents = expected_files(target)  # Validate every path before writing.
    changed = []
    for name, content in contents.items():
        p = target / name
        if p.exists() and p.read_bytes() == content:
            continue
        changed.append(name)
        print(('OUT OF DATE: ' if check else 'UPDATED: ') + name)
        if not check:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
    if not changed:
        print('Agent workspace instructions match canonical templates.')
    return int(check and bool(changed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        target = args.target.resolve(strict=True)
        if not target.is_dir():
            raise ValueError('Target must be an existing repository directory')
        return sync(target, args.check)
    except (OSError, ValueError) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
