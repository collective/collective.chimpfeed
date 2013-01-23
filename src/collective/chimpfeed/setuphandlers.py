 # encoding: utf-8
from Products.CMFCore.utils import getToolByName

catalog_indexes = (
    {'name'  : 'chimpfeeds',
     'type'  : 'KeywordIndex',
     },
    {'name'  : 'feedSchedule',
     'type'  : 'DateIndex',
     },
    {'name'  : 'feedModerate',
     'type'  : 'FieldIndex',
     },
    )
catalog_columns = ('chimpfeeds', 'feedCategory', 'feedSchedule', 'feedModerate',)
purge_existing_indexes = ()
purge_existing_columns = ()

def setup_indexes(portal, indexes, columns, purge_indexes=(),
                  purge_columns=()):
    ct = getToolByName(portal, 'portal_catalog')

    new_metadata = False

    for idx in indexes:
        if idx['name'] in purge_indexes and idx['name'] in ct.indexes():
            ct.delIndex(idx['name'])
        if idx['name'] in ct.indexes():
            print "Found the '%s' index in the catalog, nothing changed.\n" % \
                  idx['name']
        else:
            ct.addIndex(**idx)
            print "Added '%s' (%s) to the catalog.\n" % \
                  (idx['name'], idx['type'])
    for entry in columns:
        if entry in purge_columns and entry in ct.schema():
            ct.delColumn(entry)
        if entry in ct.schema():
            print "Found '%s' in the catalog metadatas, nothing changed.\n" % \
                  entry
        else:
            ct.addColumn(entry)
            print "Added '%s' to the catalog metadatas.\n" % entry
            new_metadata = True
    if new_metadata:
        print "=== portal_catalog may need re-indexing. ===\n"

def setupVarious(context):

    if context.readDataFile('collective.chimpfeed.txt') is None:
        return

    # Create indexes
    setup_indexes(portal=context.getSite(),
                  indexes=catalog_indexes,
                  columns=catalog_columns)
