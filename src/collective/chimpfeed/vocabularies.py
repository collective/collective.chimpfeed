import greatape
import base64
import time

from zope.interface import implements
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.memoize.ram import cache

from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed import logger
from collective.chimpfeed import MessageFactory as _

from Products.AdvancedQuery import Indexed, Ge
from DateTime import DateTime
from Acquisition import ImplicitAcquisitionWrapper


def stub_api(**kwargs):
    return ()


class VocabularyBase(object):
    implements(IVocabularyFactory)


class ScheduledItems(VocabularyBase):
    def __call__(self, context):
        terms = []
        today = DateTime()
        today = DateTime(today.year(), today.month(), today.day())

        query = Indexed('chimpfeeds') & Ge('feedSchedule', today)
        brains = context.portal_catalog.evalAdvancedQuery(
            query, (('feedSchedule', 'desc'), ))

        for brain in brains:
            rid = brain.getRID()
            terms.append(
                SimpleTerm(rid, brain.UID, brain.Title)
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
        if not IFeedSettings.providedBy(context):
            context = IFeedSettings(context)

        wrapped = ImplicitAcquisitionWrapper(self, context)

        generator = wrapped.get_terms()
        terms = tuple(generator)
        return SimpleVocabulary(terms)

    def api(self, **kwargs):
        api_key = self.mailchimp_api_key

        if api_key:
            api = greatape.MailChimp(api_key)

            def api(api=api, **kwargs):
                try:
                    return api(**kwargs)
                except greatape.MailChimpError, exc:
                    # http://apidocs.mailchimp.com/api/1.3/exceptions.field.php
                    if exc.code <= 0:
                        logger.critical(exc.msg)
                    elif exc.code < 120:
                        logger.warn(exc.msg)
                    elif exc.code < 200:
                        logger.info(exc.msg)
                except TypeError, exc:
                    logger.warn(exc.msg)

                return ()

        else:
            api = stub_api

        return api(**kwargs)

    @cache(lambda *args: time.time() // (5 * 60))
    def get_lists(self):
        results = []
        for result in self.api(method="lists"):
            results.append((result['id'], result['name']))

        return results

    @cache(lambda *args: time.time() // (60 * 60))
    def get_groupings(self):
        results = []

        for list_id, list_name in self.get_lists():
            groupings = self.api(
                method="listInterestGroupings", id=list_id
                )
            for grouping in groupings:
                results.append(grouping)

        return results

    @cache(lambda *args: time.time() // (60 * 60))
    def get_templates(self):
        results = []
        for result in self.api(method="campaignTemplates"):
            name = result['name']

            if name == 'Untitled Template':
                continue

            results.append(
                (result['id'], "%s (%s)" % (
                    name,
                    ", ".join(result['sections']))))

        return results


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
    def get_terms(self):
        groupings = self.get_groupings()

        for grouping in groupings:
            for term in self.get_terms_for_grouping(grouping, True):
                yield term

    def get_terms_for_grouping(self, grouping, qualified=False):
        terms = []
        for group in grouping['groups']:
            terms.append(self.get_term_for_group(group, grouping, qualified))
        return sorted(terms, key=lambda term: term.title)

    def get_term_value(self, group, grouping):
        return (grouping['id'], group['name'])

    def get_term_for_group(self, group, grouping, qualified=False):
        name = group['name']
        value = self.get_term_value(group, grouping)

        token = "%s-%s" % (
            grouping['id'],
            base64.urlsafe_b64encode(name.encode('utf-8'))
            )

        if qualified:
            name = grouping['name'] + " : " + name

        return SimpleTerm(value, token, name)


class InterestGroupStringVocabulary(InterestGroupVocabulary):
    def get_term_value(self, group, grouping):
        return "%s:%s" % (
            grouping['name'].replace(':', ''),
            group['name'].replace(':', '')
            )


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


lists_factory = ListVocabulary()
interest_groupings_factory = InterestGroupingVocabulary()
interest_groups_factory = InterestGroupVocabulary()
interest_group_strings_factory = InterestGroupStringVocabulary()
scheduled_items = ScheduledItems()
categories_factory = CategoryVocabulary()
templates = TemplateVocabulary()
