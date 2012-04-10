from zope.interface import implements
from zope.traversing.interfaces import ITraversable
from zope.component import getUtility
from zope.component import adapts

from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.AdvancedQuery import Le, Eq, In
from Acquisition import Implicit
from DateTime import DateTime

from plone.i18n.normalizer.interfaces import IURLNormalizer

from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed.interfaces import IBrowserLayer


def make_urls(feeds):
    filtered = filter(None, feeds or ())
    normalize = getUtility(IURLNormalizer).normalize

    return dict((
        ("%s.rss" % normalize(feed), feed)
        for feed in filtered
        ))


class ItemProxy(Implicit):
    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, context):
        self.context = context

    def getText(self):
        # This may raise an `AttributeError`, but that's expected.
        view = self.context.aq_inner.restrictedTraverse('@@rss-summary')

        return view()


class Feed(Implicit):
    template = ViewPageTemplateFile("feed.pt")

    max_items = 25

    __allow_access_to_unprotected_subobjects__ = 1

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

    def get_items(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        today = DateTime()

        query = In('review_state', ('visible', 'published')) & \
                Eq('chimpfeeds', self.name) & \
                Le('feedSchedule', today)

        settings = IFeedSettings(self.context)
        if settings.use_moderation:
            query = query & Eq('feedModerate', True)

        brains = catalog.evalAdvancedQuery(query)
        objects = tuple(brain.getObject() for brain in brains)
        return tuple(ItemProxy(obj).__of__(obj) for obj in objects)

    def index_html(self):
        """Publish RSS-feed."""

        return self.template()


class Feeds(Implicit):
    __allow_access_to_unprotected_subobjects__ = 1

    def __getitem__(self, name):
        settings = IFeedSettings(self)
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
