from zope.interface import implements
from zope.traversing.interfaces import ITraversable
from zope.component import getUtility
from zope.component import adapts

from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.AdvancedQuery import Le, Eq, In

from Acquisition import Acquired
from Acquisition import Implicit

from DateTime import DateTime

from plone.i18n.normalizer.interfaces import IURLNormalizer

from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed.interfaces import IBrowserLayer
from collective.chimpfeed.vocabularies import feeds_factory


def make_urls(vocabulary):
    filtered = filter(lambda term: term.title, vocabulary or ())
    normalize = getUtility(IURLNormalizer).normalize

    return tuple(
        ("%s.rss" % normalize(term.title), term.value, term.title)
        for term in sorted(
            filtered, key=lambda term: (' : ' in term.title, term.title))
        )


class ItemProxy(Implicit):
    __allow_access_to_unprotected_subobjects__ = 1

    effective_date = Acquired
    Title = Acquired

    def __init__(self, context):
        self.context = context

    @property
    def getText(self):
        # This may raise an `AttributeError`, but that's expected.
        return self.context.aq_inner.restrictedTraverse('@@rss-summary')

    def getCategory(self):
        obj = self.context.aq_inner

        try:
            field = obj.getField('feedCategory')
        except AttributeError:
            return getattr(obj, 'feedCategory', None)

        if field is not None:
            return field.get(obj)


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

        query = In('review_state', ('published', )) & \
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
        vocabulary = feeds_factory(settings)

        # Use term's titles as the basis for the feed URLs.
        for url, value, title in make_urls(vocabulary):
            if url == name:
                break
        else:
            return KeyError(name)

        return Feed(self, self.REQUEST, value)

    def pretty_title_or_id(self):
        return self.title or self.id


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
