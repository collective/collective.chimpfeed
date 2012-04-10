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


class FeedVocabulary(VocabularyBase):
    def __call__(self, context):
        normalize = getUtility(IIDNormalizer).normalize
        settings = IFeedSettings(context)

        return SimpleVocabulary([
            SimpleTerm(feed, normalize(feed), feed)
            for feed in settings.feeds or ()
            ])


class MailChimpVocabulary(VocabularyBase):
    def __call__(self, context):
        settings = IFeedSettings(context)
        wrapped = ImplicitAcquisitionWrapper(self, settings)

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
                        logger.critical(exc)
                    elif exc.code < 120:
                        logger.warn(exc)
                    elif exc.code < 200:
                        logger.info(exc)
                except TypeError, exc:
                    logger.warn(exc)

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

    @cache(lambda *args: time.time() // (5 * 60))
    def get_groupings(self):
        results = []

        for list_id, list_name in self.get_lists():
            groupings = self.api(
                method="listInterestGroupings", id=list_id
                )
            for grouping in groupings:
                results.append(grouping)

        return results


class ListVocabulary(MailChimpVocabulary):
    def get_terms(self):
        for value, name in self.get_lists():
            yield SimpleTerm(value, value, name)


class InterestGroupVocabulary(MailChimpVocabulary):
    def get_terms(self):
        groupings = self.get_groupings()

        for grouping in groupings:
            for term in self.get_terms_for_grouping(grouping):
                yield term

    def get_terms_for_grouping(self, grouping, count=True):
        for group in grouping['groups']:
            term = self.get_term_for_group(group['name'], grouping['id'])

            if count:
                term.title += " (%d)" % group['subscribers']

            yield term

    def get_term_for_group(self, name, grouping_id):
        token = "%s-%s" % (
            grouping_id,
            base64.urlsafe_b64encode(name.encode('utf-8'))
            )

        value = (grouping_id, name)
        return SimpleTerm(value, token, name)


class InterestGroupingVocabulary(MailChimpVocabulary):
    def get_terms(self):
        groupings = self.get_groupings()

        for grouping in groupings:
            value = token = grouping['id']
            groups = grouping['groups']
            name = grouping['name']

            if groups:
                name += u" (%s)" % ", ".join(
                    group['name'] for group in groups
                    )

            yield SimpleTerm(value, token, name)


feeds_factory = FeedVocabulary()
lists_factory = ListVocabulary()
interest_groupings_factory = InterestGroupingVocabulary()
interest_groups_factory = InterestGroupVocabulary()
scheduled_items = ScheduledItems()
