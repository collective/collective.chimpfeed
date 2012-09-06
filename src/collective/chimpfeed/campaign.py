import greatape

from Products.AdvancedQuery import Indexed, Ge, Le, Eq, In
from Products.Five.browser import BrowserView
from Products.statusmessages.interfaces import IStatusMessage

from DateTime import DateTime

from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed.interfaces import IGroupSorter
from collective.chimpfeed import MessageFactory as _

from zope.component import queryUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile


class CampaignView(BrowserView):
    template = ViewPageTemplateFile('campaign.pt')

    title = _(u"Preview")

    def getGroups(self, start, until=None):
        today = DateTime()
        today = DateTime(today.year(), today.month(), today.day())
        start = DateTime(start)
        start = DateTime(start.year(), start.month(), start.day())

        query = Indexed('chimpfeeds') & \
                In('review_state', ('published', )) & \
                Ge('feedSchedule', start)

        if until is not None:
            until = DateTime(until)
            query = query & Le('feedSchedule', until)

        settings = IFeedSettings(self.context)
        if settings.use_moderation:
            query = query & Eq('feedModerate', True)

        groups = {}

        for brain in self.context.portal_catalog.evalAdvancedQuery(
            query, (('feedSchedule', 'desc'), )):

            # Note that an item can appear in more than one group.
            for name in brain.chimpfeeds:
                items = groups.setdefault(name, [])
                items.append(brain)

        sorting = queryUtility(IGroupSorter)
        if sorting is None:
            key = lambda name, items: name
        else:
            key = sorting.key

        return sorted(groups.items(), key=lambda item: key(*item))


class CampaignContentView(BrowserView):
    title = _(u"Campaign created")

    def template(self):
        settings = IFeedSettings(self.context)
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

        return content['html'].decode('utf-8')
