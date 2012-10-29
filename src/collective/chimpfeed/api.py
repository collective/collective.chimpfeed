import greatape
import time

from collective.chimpfeed import logger
from collective.chimpfeed.interfaces import IApiUtility, IFeedSettings
from zope.interface import implements
from Acquisition import Implicit, aq_parent

from plone.memoize.ram import cache

def stub_api(**kwargs):
    return ()

def make_cache_key(minutes):
    def cache_key(func, inst, *args):
        api_key = inst.get_api_key()
        return time.time() // (60 * minutes), api_key, args
    return cache_key


class ApiUtility(Implicit):
    implements(IApiUtility)

    def get_api_key(self):
        settings = IFeedSettings(aq_parent(self), None)
        if settings:
            return settings.mailchimp_api_key

    def api(self, **kwargs):
        api_key = self.get_api_key()

        if api_key:
            api = greatape.MailChimp(api_key)

            def api(api=api, **kwargs):
                logger.info("mailchimp(%s)" % (", ".join(
                    "%s=%r" % item for item in kwargs.items())))

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

    @cache(make_cache_key(60))
    def _get_cached_groupings(self, list_id):
        results = []

        if list_id is None:
            list_ids = [list_id for (list_id, list_name) in self.get_lists()]
        else:
            list_ids = [list_id]

        for list_id in list_ids:
            groupings = self.api(
                method="listInterestGroupings", id=list_id
                )
            for grouping in groupings:
                results.append(grouping)

        return results

    @cache(make_cache_key(15))
    def get_lists(self):
        results = []
        for result in self.api(method="lists"):
            results.append((result['id'], result['name']))

        return results

    def get_groupings(self, list_id=None):
        if list_id is None:
            list_id = getattr(self, 'mailinglist', None)
        return self._get_cached_groupings(list_id)

    @cache(make_cache_key(60))
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

    @cache(make_cache_key(60))
    def list_merge_vars(self, list_id):
        return self.api(method="listMergeVars", id=list_id)


