import greatape

from zope.interface import Interface
from zope import schema

try:
    from zope.component.hooks import getSite
except ImportError:
    from zope.app.component.hooks import getSite

from plone.portlets.interfaces import IPortletDataProvider

from collective.chimpfeed.permissions import MODERATE_PERMISSION
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

    use_moderation = schema.Bool(
        title=_(u'Require moderation'),
        description=_(u'Select this option to enable content '
                      u'moderation.'),
        required=False,
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


class IModerationPortlet(IPortletDataProvider):
    pass


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


class IFeedControl(Interface):
    """Feed control settings."""

    feeds = schema.Set(
        title=_(u"Feeds"),
        description=_(u"If you want this content item published "
                      u"to a MailChimp RSS-feed, select one or more "
                      u"from the list below."),
        required=False,
        value_type=schema.Choice(
            vocabulary="collective.chimpfeed.vocabularies.Feeds",
            )
        )

    feedSchedule = schema.Date(
        title=_(u'Feed date'),
        description=_(u'If this date is set, the content will only be '
                      u'included in Mailchimp-based feeds from this date on. '
                      u'Otherwise, the "Publishing date" is used.'),
        required=False,
        )

    feedModerate = schema.Bool(
        title=_(u'Feed moderation'),
        description=_(u'Select this option to approve item.'),
        required=False,
        )


try:
    from plone.directives.form import Schema
    from plone.supermodel.model import Fieldset
    from plone.supermodel.interfaces import FIELDSETS_KEY
    from plone.autoform.interfaces import WRITE_PERMISSIONS_KEY
    from plone.autoform.interfaces import OMITTED_KEY
    from plone.autoform.interfaces import IAutoExtensibleForm
except ImportError:
    pass
else:
    class IFeedControl(Schema, IFeedControl):
        """Form-enabled feed control settings."""

    class moderation_enabled:
        def __nonzero__(self):
            context = getSite()
            settings = IFeedSettings(context)
            return not settings.use_moderation

    moderation_enabled = moderation_enabled()

    class settings_available:
        def __nonzero__(self):
            context = getSite()
            return IFeedSettings(context, None) is None

    settings_available = settings_available()

    IFeedControl.setTaggedValue(
        WRITE_PERMISSIONS_KEY, {
            'feedModerate': MODERATE_PERMISSION
            },
        )

    IFeedControl.setTaggedValue(
        OMITTED_KEY, (
            (IAutoExtensibleForm, 'feeds', settings_available),
            (IAutoExtensibleForm, 'feedModerate', settings_available),
            (IAutoExtensibleForm, 'feedSchedule', settings_available),
            (IAutoExtensibleForm, 'feedModerate', moderation_enabled),
            )
        )

    IFeedControl.setTaggedValue(
        FIELDSETS_KEY,
        [Fieldset(
            'dates',
            fields=['feedSchedule', 'feedModerate'],
            label=_(u"Dates")),
         Fieldset(
            'categorization',
            fields=['feeds'],
            label=_(u"Categorization")),
         ])
