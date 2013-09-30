from zope.interface import implements
from zope.component import getUtility
from zope.component import ComponentLookupError
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
try:
 # Plone < 4.3
 from zope.app.component.hooks import getSite
except ImportError:
 # Plone >= 4.3
 from zope.component.hooks import getSite  # NOQA 

from plone.i18n.normalizer.interfaces import IIDNormalizer

from collective.chimpfeed.interfaces import IFeedSettings, IApiUtility
from collective.chimpfeed import logger
from collective.chimpfeed import MessageFactory as _

from Products.AdvancedQuery import Indexed, Ge, Eq
from DateTime import DateTime
from Acquisition import ImplicitAcquisitionWrapper


class VocabularyBase(object):
    implements(IVocabularyFactory)


class ScheduledItems(VocabularyBase):
    def __call__(self, context):
        terms = []
        today = DateTime()
        today = DateTime(today.year(), today.month(), today.day())

        query = (
            Indexed('chimpfeeds') &
            Eq('allowedRolesAndUsers', 'Anonymous') &
            (Ge('feedSchedule', today) | Eq('feedModerate', False))
        )

        brains = context.portal_catalog.evalAdvancedQuery(
            query, (('feedSchedule', 'desc'),))

        for brain in brains:
            rid = brain.getRID()
            terms.append(
                SimpleTerm(rid, rid, brain.Title)
            )

        return SimpleVocabulary(terms)


class SettingVocabulary(VocabularyBase):
    field = None

    def __call__(self, context):
        normalize = getUtility(IIDNormalizer).normalize
        settings = IFeedSettings(context)
        name = self.field.__name__

        return SimpleVocabulary([
            SimpleTerm(feed, normalize(feed), feed)
            for feed in getattr(settings, name, None) or ()
            ])


class CategoryVocabulary(SettingVocabulary):
    field = IFeedSettings['categories']


class MailChimpVocabulary(VocabularyBase):
    def __call__(self, context):

        try:
            utility = getUtility(IApiUtility, context=context)
        except ComponentLookupError:
            site = getSite()
            utility = getUtility(IApiUtility, context=site)
        else:
            utility = utility.__of__(context)

        wrapped = ImplicitAcquisitionWrapper(self, utility)

        generator = wrapped.get_terms()
        terms = tuple(generator)

        try:
            return SimpleVocabulary(terms)
        except ValueError as e:
            logger.info(e.message)
            return SimpleVocabulary([])


class ListVocabulary(MailChimpVocabulary):
    def get_terms(self):
        for value, name in self.get_lists():
            yield SimpleTerm(value, value, name)


class TemplateVocabulary(MailChimpVocabulary):
    def get_terms(self):
        yield SimpleTerm(u"", "", _(u"Empty"))

        for value, name in self.get_templates():
            yield SimpleTerm(value, value, name)


class InterestGroupVocabulary(MailChimpVocabulary):
    def __init__(self, list_id=None):
        self.list_id = list_id

    def get_terms(self):
        groupings = self.get_groupings(
            self.list_id or
            getattr(self, "mailinglist", None) or
            IFeedSettings(self).mailinglist
        )

        for grouping in groupings:
            for term in self.get_terms_for_grouping(grouping, True):
                yield term

    def get_terms_for_grouping(self, grouping, qualified=False):
        terms = []
        groups = sorted(grouping['groups'],
                        key=lambda group: group['display_order'])
        for group in groups:
            terms.append(self.get_term_for_group(group, grouping, qualified))
        return terms

    def get_term_value(self, group, grouping):
        return (grouping['id'], group['name'], group['bit'])

    def get_term_for_group(self, group, grouping, qualified=False):
        name = group['name']
        value = self.get_term_value(group, grouping)

        normalize = getUtility(IIDNormalizer).normalize
        token = "%s-%s" % (grouping['id'], normalize(name))

        if qualified:
            name = grouping['name'] + " : " + name

        return SimpleTerm(value, token, name)


class InterestGroupingVocabulary(MailChimpVocabulary):
    def get_terms(self):
        groupings = self.get_groupings()

        for grouping in groupings:
            value = token = grouping['id']
            groups = grouping['groups']
            name = grouping['name']

            if groups:
                names = [group['name'] for group in groups]

                if len(names) > 4:
                    del names[4:]

                    name = _(
                        u"${name} (${groups} and ${count} more)",
                        mapping={
                            'name': name,
                            'groups': ", ".join(names),
                            'count': len(groups) - len(names),
                            }
                        )
                else:
                    name += u" (%s)" % ", ".join(names)

            yield SimpleTerm(value, token, name)

class FeedVocabulary(InterestGroupVocabulary):

    def get_term_value(self, group, grouping):
        return "%s:%s" % (
            grouping['name'].replace(':', ''),
            group['name'].replace(':', '')
            )

    def get_terms(self):
        terms = list(super(FeedVocabulary, self).get_terms())

        feeds = IFeedSettings(self).feeds

        if feeds:
            for feed in feeds:
                terms.append(SimpleTerm(feed, feed.encode('utf-8'), feed))

        return sorted(terms, key=lambda term: term.title)

    def get_groupings(self, list_id=None):
        groupings = self.aq_parent.get_groupings(list_id=list_id)

        if IFeedSettings(self).ignored_groupings:
            return [g for g in groupings if g['id'] not in \
                    IFeedSettings(self).ignored_groupings]
        return groupings



lists_factory = ListVocabulary()
interest_groupings_factory = InterestGroupingVocabulary()
interest_groups_factory = InterestGroupVocabulary()
feeds_factory = FeedVocabulary()
scheduled_items = ScheduledItems()
categories_factory = CategoryVocabulary()
templates = TemplateVocabulary()
