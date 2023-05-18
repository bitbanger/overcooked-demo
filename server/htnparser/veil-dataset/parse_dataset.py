import xml.etree.ElementTree as ET

tree = ET.parse('dataset.xml')
root = tree.getroot()

for point in root:
	print('------------------------------')
	for elem in point:
		if elem.tag == 'sentence':
			print(elem.text)
		if elem.tag == 'instruction':
			if elem.text is not None:
				for inst in elem.text.split('</span>'):
					if 'meta_instruction' not in inst:
						print(inst)
