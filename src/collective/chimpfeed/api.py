import greatape
import time

from collective.chimpfeed import logger
from collective.chimpfeed.interfaces import IApiUtility, IFeedSettings
from zope.interface import implements
from Acquisition import Implicit, aq_parent

from plone.memoize.ram import cache

def stub_api(**kwargs):
    return ()

class ApiUtility(Implicit):
    implements(IApiUtility)

    def api(self, **kwargs):
        settings = IFeedSettings(aq_parent(self))
        api_key = settings.mailchimp_api_key

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

    @cache(lambda method, self, list_id: (list_id, time.time() // (60 * 60)))
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

    @cache(lambda *args: time.time() // (15 * 60))
    def get_lists(self):
        results = []
        for result in self.api(method="lists"):
            results.append((result['id'], result['name']))

        return results

    def get_groupings(self, list_id=None):
        if list_id is None:
            list_id = getattr(self, 'mailinglist', None)
        return self._get_cached_groupings(list_id)

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
