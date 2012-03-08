from zope.interface import implements
from zope.component import adapts
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.field import ExtensionField
from plone.indexer.decorator import indexer

from Products.Archetypes import atapi
from Products.Archetypes.interfaces import IBaseContent

from collective.chimpfeed import MessageFactory as _
from collective.chimpfeed.permissions import MODERATE_PERMISSION


@indexer(IBaseContent)
def feed_indexer(context):
    feeds = context.getField('feeds').get(context)
    return [unicode(feed, 'utf-8') for feed in feeds]


class ScheduleField(ExtensionField, atapi.DateTimeField):
    def set(self, instance, value, **kwargs):
        previous = self.get(instance, **kwargs)

        # Set moderation to `False` to prompt an editor to moderate
        # new date.
        if previous == value:
            return

        instance.getField('feedModerate').set(instance, False)
        super(ScheduleField, self).set(instance, value, **kwargs)


class LinesField(ExtensionField, atapi.LinesField):
    pass


class ModerationField(ExtensionField, atapi.BooleanField):
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

        ScheduleField(
            'feedSchedule',
            schemata="settings",
            languageIndependent=True,
            required=False,
            default=None,
            widget=atapi.CalendarWidget(
                show_hm=False,
                starting_year=2012,
                ending_year=2015,
                label=_(u'Schedule feed date'),
                description=_(u'The item will be scheduled to be included '
                              u'in feeds from this date. Note that this '
                              u'is subject to editor moderation.'),
                ),
            ),

        ModerationField(
            'feedModerate',
            schemata="settings",
            default=False,
            enforceVocabulary=1,
            write_permission=MODERATE_PERMISSION,
            widget=atapi.BooleanWidget(
                label=_(u'Approve schedule'),
                description=_(u'Select this option to approve schedule.'),
                ),
            ),
        )

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields
