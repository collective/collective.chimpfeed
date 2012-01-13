from zope.interface import implements
from zope.component import adapts
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.field import ExtensionField
from collective.chimpfeed import MessageFactory as _
from plone.indexer.decorator import indexer

from Products.Archetypes import atapi
from Products.Archetypes.interfaces import IBaseContent


@indexer(IBaseContent)
def feed_indexer(context):
    feeds = context.getField('feeds').get(context) or ()
    return [unicode(feed, 'utf-8') for feed in feeds]


class LinesField(ExtensionField, atapi.LinesField):
    pass


class FeedExtender(object):
    implements(ISchemaExtender)
    adapts(IBaseContent)

    fields = (
        LinesField(
            name="feeds",
            required=False,
            multivalued=1,
            schemata="settings",
            widget=atapi.MultiSelectionWidget(
                label=_("Feeds"),
                description=_(u"If you want this content item published "
                              u"to a news feed, select one or more from "
                              u"the list below."),
                ),
            vocabulary_factory="collective.chimpfeed.vocabularies.Feeds",
            ),
        )

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields
