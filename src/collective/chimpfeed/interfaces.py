import greatape

from zope.interface import Interface
from zope import schema

from plone.portlets.interfaces import IPortletDataProvider

from collective.chimpfeed import MessageFactory as _
from collective.chimpfeed import logger


def check_api_key(api_key):
    if not api_key:
        return True

    api = greatape.MailChimp(api_key)

    try:
        api(method="ping")
    except greatape.MailChimpError:
        pass
    except ValueError, exc:
        logger.warn(exc)
    else:
        return True

    return False


class INameSplitter(Interface):
    def split_name(fullname):
        """Return (fname, lname) tuple."""


class IBrowserLayer(Interface):
    """Theme-specific browser-layer."""


class IFeedSettings(Interface):
    mailchimp_api_key = schema.TextLine(
        title=_(u"MailChimp API key"),
        description=_(u"This key is associated to your "
                      u"account with MailChimp."),
        required=False,
        default=u"",
        constraint=check_api_key,
        )

    feeds = schema.List(
        title=_(u"Feeds"),
        description=_(u"Use this field to set up your feeds. "
                      u"Give each feed a title such as \"News\"; "
                      u"one feed per line."),
        required=False,
        value_type=schema.TextLine(),
        )


class ISubscriptionFormSettings(Interface):
    mailinglist = schema.Choice(
        title=_(u"Mailinglist"),
        description=_(u"Select a mailinglist for this portlet."),
        vocabulary="collective.chimpfeed.vocabularies.Lists",
        required=True,
        )

    interest_groupings = schema.Tuple(
        title=_(u"Interest groups"),
        description=_(u"Select interest groups. "
                      u"Note that all interests within the selected "
                      u"groups will appear in the portlet."),
        value_type=schema.Choice(
            vocabulary="collective.chimpfeed.vocabularies.InterestGroupings",
            ),
        required=False,
        )

    interest_groups = schema.Tuple(
        title=_(u"Interests"),
        description=_(u"Select interests. "
                      u"The number listed in each parenthesis is "
                      u"the current number of subscribers with "
                      u"that interest."),
        value_type=schema.Choice(
            vocabulary="collective.chimpfeed.vocabularies.InterestGroups",
            ),
        required=False,
        )


class ISubscriptionPortlet(IPortletDataProvider, ISubscriptionFormSettings):
    heading = schema.TextLine(
        title=_(u"Title"),
        description=_(u"Provide a title for the portlet."),
        required=True,
        default=u"Sign up",
        )


class IControlPanel(IFeedSettings):
    urls = schema.Tuple(
        title=_(u"URLs"),
        description=_(u"These correspond to the feeds given above. "
                      u"Copy the URL into MailChimp when setting up one "
                      u"or more RSS-campaigns."),
        required=False,
        value_type=schema.ASCIILine(),
        )
