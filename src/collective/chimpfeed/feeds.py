from zope.interface import implements
from zope.traversing.interfaces import ITraversable
from zope.component import getUtility
from zope.component import adapts

from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.AdvancedQuery import Indexed, Le, Eq, In
from Acquisition import Implicit
from DateTime import DateTime

from plone.i18n.normalizer.interfaces import IURLNormalizer
from plone.registry.interfaces import IRegistry

from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed.interfaces import IBrowserLayer


def make_urls(feeds):
    filtered = filter(None, feeds or ())
    normalize = getUtility(IURLNormalizer).normalize

    return dict((
        ("%s.rss" % normalize(feed), feed)
        for feed in filtered
        ))


class Feed(Implicit):
    template = ViewPageTemplateFile("feed.pt")

    max_items = 25

    def __init__(self, context, request, name):
        self.context = context
        self.request = request
        self.name = name

    def HEAD(self, *args):
        """Handle HEAD-request."""

        response = self.template()
        self.request.response.setHeader('Content-Length', len(response))

        # Actually return an empty string
        return u""

    def get_brains(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        today = DateTime()

        query = In('review_state', ('visible', 'published')) & \
                Eq('chimpfeeds', self.name) & \
                Eq('feedModerate', True) & \
                Le('feedSchedule', today)

        brains = catalog.evalAdvancedQuery(query)
        return tuple(brains)

    def index_html(self):
        """Publish RSS-feed."""

        return self.template()


class Feeds(Implicit):
    def __getitem__(self, name):
        settings = getUtility(IRegistry).forInterface(IFeedSettings)
        urls = make_urls(settings.feeds)
        name = urls[name]
        return Feed(self, self.REQUEST, name)


class FeedTraverser(object):
    implements(ITraversable)
    adapts(ISiteRoot, IBrowserLayer)

    def __init__(self, context, request=None):
        self.context = context
        self.request = request

    def traverse(self, name, ignore):
        feeds = Feeds()

        if name:
            return feeds[name]

        return feeds
