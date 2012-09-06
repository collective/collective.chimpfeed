import logging
import weakref

from zope.interface import implements
from zope.interface import alsoProvides
from zope.component import adapts
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.field import ExtensionField
from plone.indexer.decorator import indexer

from Acquisition.interfaces import IAcquirer
from Acquisition import aq_base

from Products.Archetypes import atapi
from Products.Archetypes.interfaces import IBaseContent
from DateTime import DateTime

from collective.chimpfeed.permissions import MODERATE_PERMISSION
from collective.chimpfeed.interfaces import IFeedControl
from collective.chimpfeed.interfaces import IFeedSettings


try:
    from plone.app.dexterity.behaviors.metadata import Categorization
    from plone.app.dexterity.behaviors.metadata import DCFieldProperty
except ImportError:
    pass
else:
    class FeedControl(Categorization):
        feeds = DCFieldProperty(IFeedControl['feeds'])
        feedCategory = DCFieldProperty(IFeedControl['feedCategory'])
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


@indexer(IBaseContent)
def at_schedule_indexer(context):
    schedule = context.getField('feedSchedule').get(context)
    if schedule is None:
        return context.getField('effectiveDate').get(context)

    return schedule

@indexer(IBaseContent)
def at_category_indexer(context):
    category = context.getField('feedCategory').get(context)
    if category is not None:
        return unicode(category, 'utf-8')


try:
    from plone.dexterity.interfaces import IDexterityContent
except ImportError:
    pass
else:
    from plone.behavior.interfaces import IBehaviorAssignable
    from plone.app.dexterity.behaviors.metadata import IDublinCore

    @indexer(IDexterityContent)
    def dx_schedule_indexer(context):
        assignable = IBehaviorAssignable(context, None)
        if assignable is None or not assignable.supports(IFeedControl):
            return

        date = getattr(context, "feedSchedule", None)
        if date is None:
            assignable = IBehaviorAssignable(context, None)
            if assignable is not None:
                if assignable.supports(IDublinCore):
                    return context.effective_date

        return DateTime(
            date.year,
            date.month,
            date.day
            )

    @indexer(IDexterityContent)
    def dx_feed_indexer(context):
        assignable = IBehaviorAssignable(context, None)
        if assignable is not None:
            if assignable.supports(IFeedControl):
                try:
                    return tuple(context.feeds)
                except TypeError:
                    return tuple()

    @indexer(IDexterityContent)
    def dx_category_indexer(context):
        assignable = IBehaviorAssignable(context, None)
        if assignable is not None:
            if assignable.supports(IFeedControl):
                return getattr(context, "feedCategory", None)


class StringField(ExtensionField, atapi.StringField):
    pass


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
        super(ModerationField, self).set(instance, value, **kwargs)

        date = schedule.get(instance)
        if date is None:
            return


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

        StringField(
            'feedCategory',
            schemata="settings",
            languageIndependent=True,
            required=False,
            default=None,
            widget=atapi.SelectionWidget(
                label=IFeedControl['feedCategory'].title,
                description=IFeedControl['feedCategory'].description
                ),
            vocabulary_factory=IFeedControl['feedCategory'].vocabularyName,
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
        if IAcquirer.providedBy(self.context):
            base = aq_base(self.context)
        else:
            base = self.context

        cls = type(base)
        applicable = self.types.get(cls)
        if applicable is None:
            # Check that we can get a settings object for this
            # context.
            applicable = IFeedSettings(self.context, None) is not None

            if applicable:
                # If there's an overlap on field names, we do not extend
                # the content schema. Note that Archetypes allows
                # overriding a field which is why we need to perform this
                # check ourselves.
                names = set(field.__name__ for field in self.fields)
                existing = self.context.schema.keys()
                overlap = names & set(existing)
                applicable = not bool(overlap)

            self.types[cls] = applicable

            if not applicable:
                logging.getLogger('collective.chimpfeed').info(
                    "skipping %s." % cls.__name__
                    )

        if not applicable:
            return ()

        return self.fields
