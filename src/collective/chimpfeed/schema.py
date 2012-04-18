import logging
import weakref

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

        storage = instance.getField('feedModerate').getStorage()
        storage.set('feedModerate', instance, False, **kwargs)

        super(ScheduleField, self).set(instance, value, **kwargs)


class LinesField(ExtensionField, atapi.LinesField):
    pass


class ModerationField(ExtensionField, atapi.BooleanField):
    def set(self, instance, value, **kwargs):
        schedule = instance.getField('feedSchedule')
        date = schedule.get(instance)

        today = DateTime()
        today = DateTime(today.year(), today.month(), today.day())

        # Bump the scheduled date to today's date. This ensures that
        # the item will be shown on the moderation portlet.
        if date < today:
            schedule.set(instance, today)

        super(ModerationField, self).set(instance, value, **kwargs)


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
            vocabulary_factory=IFeedControl['feeds'].value_type.vocabularyName,
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

    types = weakref.WeakKeyDictionary()

    def __init__(self, context):
        self.context = context

    def getFields(self):
        cls = type(self.context.aq_base)
        applicable = self.types.get(cls)
        if applicable is None:
            # If there's an overlap on field names, we do not extend
            # the content schema. Note that Archetypes allows
            # overriding a field which is why we need to perform this
            # check ourselves.
            names = set(field.__name__ for field in self.fields)
            existing = self.context.schema.keys()
            overlap = names & set(existing)
            applicable = self.types[cls] = not bool(overlap)

            if not applicable:
                logging.getLogger('collective.chimpfeed').warn(
                    "Unable to extend schema for: %s." % cls.__name__
                    )

        if not applicable:
            return ()

        return self.fields
