from zope.component import ComponentLookupError
from collective.chimpfeed.interfaces import IFeedSettings

try:
    from plone.registry.interfaces import IRegistry
except ImportError:
    from collective.chimpfeed.legacy import annotation_proxy

    def get_settings(context):
        site = context.portal_url.getPortalObject()
        return annotation_proxy(site, IFeedSettings)
else:
    from zope.component import getUtility

    def get_settings(context):
        try:
            return getUtility(IRegistry).forInterface(IFeedSettings)
        except KeyError:
            raise ComponentLookupError(IFeedSettings)
