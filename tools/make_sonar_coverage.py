#!/usr/bin/env python3
"""
Convert coverage.py XML to the Sonar Generic Coverage format:
- Picks up <sources><source> to compute relative file paths
- Produces <coverage><files><file name="...">...</file></files></coverage>
Usage:
  python3 tools/make_sonar_coverage.py reports/coverage.xml reports/coverage-for-sonar.xml
"""
import sys, os
import xml.etree.ElementTree as ET
def to_rel(base, path):
    # if path already has base, make it relative; else return as-is
    try:
        return os.path.relpath(os.path.join(base, path), start=os.getcwd())
    except Exception:
        return path

def convert(inp, outp):
    tree = ET.parse(inp)
    root = tree.getroot()
    # ensure version attribute Sonar likes
    root.set('version', '1')

    # find first <source> if present to compute relative paths
    source_base = None
    sources = root.find('sources')
    if sources is not None:
        s = sources.find('source')
        if s is not None and s.text:
            source_base = s.text.strip()

    # Build new root
    new_root = ET.Element('coverage', root.attrib)
    files_parent = ET.Element('files')

    # iterate through any <package>/<classes>/<class> or <files>/<file>
    # handle both original coverage.py structure and earlier converted forms
    # find all class/file entries
    # prefer existing <file> nodes if present
    file_nodes = []
    for f in root.findall('.//file'):
        file_nodes.append(('file', f))
    for cls in root.findall('.//class'):
        file_nodes.append(('class', cls))

    # keep track of names added to avoid duplicates
    seen = set()
    for kind, node in file_nodes:
        if kind == 'file':
            name = node.get('name')
            lines = node.find('lines')
        else:  # class
            name = node.get('filename') or node.get('name')
            lines = node.find('lines')
        if not name or lines is None:
            continue
        # compute relative path: if source_base present, prefix; else assume file under app/
        if source_base:
            relname = to_rel(source_base, name)
        else:
            # if name already contains '/', keep it; otherwise assume under app/
            relname = name if '/' in name else os.path.join('app', name)
        # normalize to unix style
        relname = relname.replace('\\', '/')
        if relname in seen:
            continue
        seen.add(relname)
        file_elem = ET.Element('file', {'name': relname})
        # copy lines (create new <lines> and copy <line> children)
        lines_elem = ET.Element('lines')
        for ln in list(lines):
            # ensure tag is 'line'
            if ln.tag.lower() != 'line':
                continue
            # create new line element with number and hits
            num = ln.get('number') or ln.get('lineNumber') or ln.get('num')
            hits = ln.get('hits') or ln.get('hits') or ln.get('count') or '0'
            new_line = ET.Element('line', {'number': str(num), 'hits': str(hits)})
            lines_elem.append(new_line)
        file_elem.append(lines_elem)
        files_parent.append(file_elem)
    new_root.append(files_parent)

    # write out
    tree2 = ET.ElementTree(new_root)
    tree2.write(outp, encoding='utf-8', xml_declaration=True)
    print(f"Written Sonar-friendly coverage to: {outp}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: make_sonar_coverage.py <in-coverage.xml> <out-coverage-for-sonar.xml>')
        sys.exit(2)
    convert(sys.argv[1], sys.argv[2])
