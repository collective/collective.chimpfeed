import greatape

from zope.component import getUtilitiesFor

from Products.AdvancedQuery import Indexed, Ge, Le, Eq, In
from Products.Five.browser import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from Products.CMFCore.utils import getToolByName

from DateTime import DateTime

from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed.interfaces import IGroupSorter
from collective.chimpfeed.interfaces import IGroupExtras
from collective.chimpfeed import MessageFactory as _

from collective.chimpfeed.vocabularies import InterestGroupVocabulary

from zope.component import queryUtility
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class CampaignView(BrowserView):
    template = ViewPageTemplateFile('campaign.pt')

    title = _(u"Preview")

    def results(self, start, until=None):
        today = DateTime()
        today = DateTime(today.year(), today.month(), today.day())
        start = DateTime(start)
        start = DateTime(start.year(), start.month(), start.day())

        query = Indexed('chimpfeeds') & \
                In('review_state', ('published', )) & \
                Ge('feedSchedule', start)

        if until:
            try:
                until = DateTime(until)
            except DateTime.SyntaxError:
                pass
            else:
                query = query & Le('feedSchedule', until)

        site = getToolByName(self.context, "portal_url").getPortalObject()
        settings = IFeedSettings(site)
        if settings.use_moderation:
            query = query & Eq('feedModerate', True)

        catalog = getToolByName(self.context, "portal_catalog")

        extras = []
        utilities = getUtilitiesFor(IGroupExtras)
        groups = InterestGroupVocabulary()(self.context)
        for name, util in utilities:
            for group in groups:
                extras.extend(util.items(group.title, start, until))

        return list(catalog.evalAdvancedQuery(
            query, (('feedSchedule', 'desc'), ))) + extras
        

    def getGroupings(self, start, until=None):
        groupings = {}
        for brain in self.results(start, until=until):

            # Note that an item can appear in more than one group.
            categories = [name.rsplit(':', 1)[0] for name in brain.chimpfeeds]
            for category in set(categories):
                items = groupings.setdefault(category, [])
                items.append(brain)

        sorting = queryUtility(IGroupSorter)
        if sorting is None:
            key = lambda name, items: name
        else:
            key = sorting.key

        return sorted(groupings.items(), key=lambda item: key(*item))

    def getSegments(self, start, until=None, **kwargs):
        chimpfeeds = set()
        for brain in self.results(start, until=until):
            chimpfeeds.update(
                (feed.replace(' ', '') for feed in brain.chimpfeeds)
            )

        segments = {}
        
        for term in InterestGroupVocabulary()(self.context):
            if term.title.replace(' ', '') in chimpfeeds:
                groupingid, grouptitle, groupid = term.value
                items = segments.setdefault(groupingid, [])
                items.append(groupid)
                
        return segments

class CampaignContentView(BrowserView):
    title = _(u"Campaign created")

    def template(self):
        site = getToolByName(self.context, "portal_url").getPortalObject()
        settings = IFeedSettings(site)
        api_key = settings.mailchimp_api_key

        if not api_key:
            return

        try:
            api = greatape.MailChimp(api_key, debug=False)
            cid = self.request.get('cid', '')
            content = api(method="campaignContent", cid=cid)
        except greatape.MailChimpError:
            IStatusMessage(self.request).addStatusMessage(
                _(u"Unable to show content."), "error"
                )
            return

        return content['html']
