from zope.interface import implements
from zope.interface import alsoProvides
from zope.component import adapts
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.field import ExtensionField
from plone.indexer.decorator import indexer

from Products.Archetypes import atapi
from Products.Archetypes.interfaces import IBaseContent
from DateTime import DateTime

from collective.chimpfeed.permissions import MODERATE_PERMISSION
from collective.chimpfeed.interfaces import IFeedControl


try:
    from plone.app.dexterity.behaviors.metadata import Categorization
    from plone.app.dexterity.behaviors.metadata import DCFieldProperty
except ImportError:
    pass
else:
    class FeedControl(Categorization):
        feeds = DCFieldProperty(IFeedControl['feeds'])
        feedSchedule = DCFieldProperty(IFeedControl['feedSchedule'])
        feedModerate = DCFieldProperty(IFeedControl['feedModerate'])


try:
    from plone.autoform.interfaces import IFormFieldProvider
except ImportError:
    pass
else:
    alsoProvides(IFeedControl, IFormFieldProvider)


@indexer(IBaseContent)
def at_feed_indexer(context):
    feeds = context.getField('feeds').get(context)
    return tuple(unicode(feed, 'utf-8') for feed in feeds)


try:
    from plone.dexterity.interfaces import IDexterityContent
except ImportError:
    pass
else:
    @indexer(IDexterityContent)
    def dx_schedule_indexer(context):
        date = context.feedSchedule
        return DateTime(
            date.year,
            date.month,
            date.day
            )

    @indexer(IDexterityContent)
    def dx_feed_indexer(context):
        if IFeedControl.providedBy(context):
            return tuple(context.feeds)

        # To-Do: It seems that we can't check for the behavior in this
        # way.
        return getattr(context, "feeds", None)


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
                label=IFeedControl['feeds'].title,
                description=IFeedControl['feeds'].description,
                ),
            vocabulary_factory=IFeedControl['feeds'].value_type.vocabulary,
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
                label=IFeedControl['feedSchedule'].title,
                description=IFeedControl['feedSchedule'].description
                ),
            ),

        ModerationField(
            'feedModerate',
            schemata="settings",
            default=False,
            enforceVocabulary=1,
            write_permission=MODERATE_PERMISSION,
            widget=atapi.BooleanWidget(
                label=IFeedControl['feedModerate'].title,
                description=IFeedControl['feedModerate'].description,
                ),
            ),
        )

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields
