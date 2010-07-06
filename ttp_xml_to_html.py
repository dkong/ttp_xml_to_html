# Generates an index page with all bugs and a separate page for each bug with 
# full detailed information.  Also renames attachments to original filenames.
#
# Steps:
#  Open TTP
#  Select/Highlight the defects you want
#  File -> Export -> XML Export
#  Check the box "Export file attachments" (if you want attachments)
#  Uncheck the box "Export formatting and images"
#  Leave everything else with the default values
#  Click "Export" button
#  Choose save location
#  Wait a couple minutes (depending on number of defects and attachments)
#  Once its finished, unzip the archive
#  Run this python script with the unzipped location as the only argument
#  Once its finished (see output), open browser to index.html in the location

import os
import sys
from xml.dom.minidom import parse, parseString

if len(sys.argv) != 2:
    print 'Usage: python %s <path_to_unzipped_xml_export>' % (sys.argv[0])
    sys.exit(-1)

rootDir = sys.argv[1]
xmlFile = os.path.join(rootDir, 'archive_manifest.xml')
htmlFull = os.path.join(rootDir, 'index.html')

if not os.path.exists(xmlFile):
    print 'Error "%s" does not exist.  Did you type the correct directory?' % xmlFile
    sys.exit(-1)

defectsList = []

# Note: The TTP XML exporter has some incorrect fields, for example the component
# value is contained in the priority elment.  Not sure if the exporter is wrong or 
# or the new fields were setup incorrectly in the backend.
xml_element_to_friendly_name = { 'record-id':'id', 
        'summary':'summary',
        'type':'severity',
        'priority':'component',
        'severity':'rate',
        'date-entered':'date',
        'defect-status':'status' }

# TODO: There's a bug where you can't sort the last column.  I confirmed the bug is not
# positional nor is it related to the column data.
allColumnOrder = ['id', 'summary', 'severity', 'status', 'assigned', 'component' ]


def RenameAttachmentsToOriginal():
    datToOriginal = {}
    dom1 = parse(xmlFile)
    defects = dom1.getElementsByTagName('defect')
    for defect in defects:
        records = defect.getElementsByTagName('reported-by-record')
        for record in records:
            attachments = record.getElementsByTagName('attachment')
            for attachment in attachments:
                datFilename = os.path.join(rootDir, attachment.getAttribute('filespec'))
                originalFilename = os.path.join(rootDir, attachment.getAttribute('name'))
                datToOriginal[datFilename] = originalFilename

    rename_count = 0
    for dat, original in datToOriginal.items():
        if not os.path.exists(dat):
            #print "%s doesn't exist - skipping" % (dat)
            continue

        if os.path.exists(original):
            #print "%s already exists - skipping rename from %s" % (original, dat)
            continue

        os.rename(dat, original)
        rename_count = rename_count + 1

    if rename_count > 0:
        print 'Successfully renamed %d files' % (rename_count)

class Defect:
    def __init__(self):
        self.data = {}

    def Get(self, key):
        if self.data.has_key(key) and self.data[key]:
            return self.data[key].encode('ascii', 'ignore')
        return None

    def WriteHTML(self, filename):
        """ Write out all information associated with this defect """

        f = open(filename, 'wt')
        f.write('<html>\n')
        f.write('<head>\n')
        f.write('<title>%s - %s</title>\n' % (self.data['id'], self.data['summary'].encode('ascii', 'ignore')))
        f.write('</head>\n')
        f.write('<body>\n')

        f.write('<table border="1">\n')
        f.write('<tr> <td>%s</td> <td>%s</td> <td>Assigned: %s</td> <td>Component: %s</td> </tr>\n' % (self.Get('id'), self.Get('status'), " and ".join(self.data['assigned']), self.Get('component')))
        f.write('<tr> <td>Sev: %s</td> <td>Rate: %s</td> <td>Reporter: %s</td> <td>Opened: %s</td> <td>%s</td> </tr>\n' % (self.Get('severity'), self.Get('rate'), self.data['reporter'][0], self.Get('date'), self.Get('found_version')))
        f.write('</table>\n')

        f.write('<h2>%s</h2>\n' % (self.Get('summary')))
        f.write('<pre>%s</pre>\n' % (self.Get('description')))

        # Defect events
        defectEvents = self.data['defect_events']
        if len(defectEvents) > 0:
            f.write('<table border="1">\n')
            for event in defectEvents:
                f.write('<tr> <td>%s</td> <td>%s</td> <td>%s</td>' % (event['date'], event['author'][0], event['name']))
                if event.has_key('assigned'):
                    f.write('<td>Assigned To: %s</td>' % (" and ".join(event['assigned'])))
                if event.has_key('notes') and event['notes']:
                    f.write('<td>%s</td>' % (event['notes']))
                if event.has_key('fixed_version') and event['fixed_version']:
                    f.write('<td>Fixed Version: %s</td>' % (event['fixed_version']))
                f.write('</tr>')
            f.write('</table>\n')

        # List of non image attachments
        if self.data.has_key('attachments'):
            for value in self.data['attachments']:
                filename = value['filename']
                date = value['date']
                if filename.lower().find('.jpg') == -1:
                    f.write('<br><a href="%s">%s - %s</a>\n' % (filename, filename, date))

        # Display image attachments
        f.write('<br>')
        if self.data.has_key('attachments'):
            for value in self.data['attachments']:
                filename = value['filename']
                date = value['date']
                if filename.lower().find('.jpg') != -1:
                    f.write('<br><a href="%s">%s - %s</a>\n' % (filename, filename, date))
                    f.write('<br><img src="%s" alt="%s" /><br>\n' % (filename, filename))

        f.write('</body>\n')
        f.write('</html>\n')
        f.close()

def GetXmlValue(element, element_name):
    elements = element.getElementsByTagName(element_name)
    if len(elements) == 1:
        if len(elements[0].childNodes) == 1:
            return elements[0].childNodes[0].data

    return None

def GetNameValue(element, element_name):
    namesList = []
    names = element.getElementsByTagName(element_name)
    for name in names:
        first_name = GetXmlValue(name, 'first-name')
        last_name = GetXmlValue(name, 'last-name')
        namesList.append("%s, %s" % (last_name, first_name))
        
    return namesList

def GetAttachmentsValue(element):
    attachmentsList = []
    records = element.getElementsByTagName('reported-by-record') 
    for record in records:
        attachments = record.getElementsByTagName('attachment')
        for attachment in attachments:
            filename = attachment.getAttribute('name') 
            create_date = attachment.getAttribute('create-date') 
            attachmentsList.append({'filename':filename, 'date':create_date})

    return attachmentsList

def GetDefectEventsValue(element):
    defectEventsList = []
    defectEvents = element.getElementsByTagName('defect-event')
    for defectEvent in defectEvents:
        d = {}
        d['name'] = GetXmlValue(defectEvent, 'event-name')
        d['date'] = GetXmlValue(defectEvent, 'event-date')
        d['author'] = GetNameValue(defectEvent, 'event-author')
        d['notes'] = GetXmlValue(defectEvent, 'notes')
        d['fixed_version'] = GetCustomFieldValue(defectEvent, 'Fix Version')

        assignedElement = defectEvent.getElementsByTagName('event-assigned-to')
        if len(assignedElement) == 1:
            d['assigned'] = GetNameValue(assignedElement[0], 'assigned-to-user')

        defectEventsList.append(d)

    return defectEventsList

def GetDescriptionValue(element):
    elements = element.getElementsByTagName('reported-by-record') 
    if len(elements) == 1:
        return GetXmlValue(elements[0], 'description')

    return attachmentsList

def GetCustomFieldValue(element, element_name):
    elements = element.getElementsByTagName('custom-field-value')
    for element in elements:
        field_name = element.getAttribute('field-name') 
        if field_name and field_name.lower() == element_name.lower():
            return element.getAttribute('field-value')

    return None

def ParseDefects():
    """ Parse the XML for the data we care about"""

    dom1 = parse(xmlFile)
    defectsElements = dom1.getElementsByTagName('defect')
    for defectElement in defectsElements:
        defect = Defect()
        defectsList.append(defect)

        for xml_name, friendly_name in xml_element_to_friendly_name.items():
            value = GetXmlValue(defectElement, xml_name)
            if value:
                defect.data[friendly_name] = value

        defect.data['assigned'] = GetNameValue(defectElement, 'currently-assigned-to')
        defect.data['reporter'] = GetNameValue(defectElement, 'entered-by')
        defect.data['attachments'] = GetAttachmentsValue(defectElement)
        defect.data['description'] = GetDescriptionValue(defectElement)
        defect.data['found_version'] = GetCustomFieldValue(defectElement, 'found on build')
        defect.data['defect_events'] = GetDefectEventsValue(defectElement)
        
def GetSeverityCount(defects):
	a = b = c = other = 0
	for defect in defects:
		if defect.data.has_key('severity'):
			severity = defect.data['severity']
			if severity:
				severity = severity.lower()
				if severity == 'a':
					a = a + 1
				elif severity == 'b':
					b = b + 1
				elif severity == 'c':
					c = c + 1
				else:
					other = other + 1
			else:
				other = other + 1
	return (a, b, c, other)
			

def WriteFullHTML(filename, defects):
    """ Write out a single HTML file containing a table of defects"""

    f = open(filename, 'wt')
    f.write('<html>\n')
    f.write('<head>\n')
    f.write('<script src="http://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>')

    f.write("""
    <style type="text/css">
    /* Sortable tables */
    table.sortable thead {
        background-color:#eee;
            color:#666666;
                font-weight: bold;
                    cursor: default;
    }
    </style>
    """)

    a, b, c, other = GetSeverityCount(defectsList)
    f.write('<title>TTP Database - %d Defects - A: %d + B: %d + C: %d + Other: %d</title>\n' % (len(defects), a, b, c, other))
    f.write('</head>\n')
    f.write('<body><table class="sortable" border="1">\n')

    f.write('<tr>')
    for column in allColumnOrder:
        f.write('<th>%s</th>' % (column))
    f.write('</tr>\n')

    for defect in defects:
        f.write('<tr>')
        for column in allColumnOrder:
            if defect.data.has_key(column):
                value = defect.data[column]
                if value and column == 'id':
                    f.write('<td><a href=%s>%s</a></td>\n' % (value + '.html', value))
                if value and column == 'assigned':
                    f.write('<td>%s</td>' % (" and ".join(value)))
                elif value:
                    value = defect.data[column].encode('ascii', 'ignore')
                    f.write('<td>%s</td>' % (value))
        f.write('</tr>\n')

    f.write('</table></body>\n')
    f.write('</html>\n')
    f.close()

    print 'Successfully generated index page'
    print 'Open your browser at %s' % (filename)

def WriteIndividualHTML(defects):
    for defect in defects:
        filename = os.path.join(rootDir, defect.data['id'] + '.html')
        defect.WriteHTML(filename)

    if len(defects) > 0:
        print 'Successfully generated %d defect pages' % (len(defects))

RenameAttachmentsToOriginal()
ParseDefects()
WriteIndividualHTML(defectsList)
WriteFullHTML(htmlFull, defectsList)
