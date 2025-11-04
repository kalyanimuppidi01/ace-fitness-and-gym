#!/usr/bin/env python3
import sys, xml.etree.ElementTree as ET
def convert(input_path, output_path):
    tree = ET.parse(input_path)
    root = tree.getroot()
    root.set('version', '1')
    for sources in root.findall('sources'):
        root.remove(sources)
    for pkg in root.findall('.//package'):
        classes = pkg.find('classes')
        if classes is None:
            continue
        files_elem = ET.Element('files')
        for cls in list(classes.findall('class')):
            filename = cls.get('filename') or cls.get('name') or 'unknown'
            file_elem = ET.Element('file', {'name': filename})
            for child in list(cls):
                file_elem.append(child)
            files_elem.append(file_elem)
            classes.remove(cls)
        pkg.append(files_elem)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    print(f"Converted '{input_path}' -> '{output_path}'")
if __name__ == '__main__':
    if len(sys.argv)!=3:
        print('Usage: convert_coverage_for_sonar.py <in> <out>'); sys.exit(2)
    convert(sys.argv[1], sys.argv[2])
