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


class IApiUtility(Interface):
    """ Api utuility """

class IGroupSorter(Interface):
    def key(name, items):
        """Return sorting key for group with the provided name and
        items."""


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

    mailinglist = schema.Choice(
        title=_(u"Interest group list"),
        description=_(u"Use this field to automatically "
                      u"pull interest groups from a list. "
                      u"The interest groups are "
                      u"added to the list of feeds "
                      "and kept up to date every hour."
                      ),
        required=False,
        vocabulary="collective.chimpfeed.vocabularies.Lists",
        )

    feeds = schema.List(
        title=_(u"Feeds"),
        description=_(u"The strings listed in this field "
                      u"are available for tagging on "
                      u"applicable site content. Please use "
                      u"one value per line. An RSS-feed "
                      u"is automatically available for each "
                      u"string (links are shown below). Note "
                      u"that it's possible to select a "
                      u"subscription list (see above) "
                      u"and pull additional strings from "
                      u"its interest groups."
                      ),
        required=False,
        value_type=schema.TextLine(),
        )

    categories = schema.List(
        title=_(u"Categories"),
        description=_(u"List the available feed categories."),
        required=False,
        value_type=schema.TextLine(),
        )

    use_moderation = schema.Bool(
        title=_(u'Require moderation'),
        description=_(u'Select this option to enable content '
                      u'moderation.'),
        required=False,
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
        description=_(u"Select interests."),
        value_type=schema.Choice(
            vocabulary="collective.chimpfeed.vocabularies.InterestGroups",
            ),
        required=False,
        )


class ICampaignPortlet(IPortletDataProvider):
    mailinglist = schema.Choice(
        title=_(u"Mailinglist"),
        description=_(u"Select a mailinglist for this portlet."),
        vocabulary="collective.chimpfeed.vocabularies.Lists",
        required=True,
        )

    template = schema.Choice(
        title=_(u"Template"),
        description=_(u"Select a campaign template."),
        required=False,
        default=u"",
        vocabulary="collective.chimpfeed.vocabularies.Templates",
        )

    section = schema.TextLine(
        title=_(u"Section"),
        description=_(u"In MailChimp, templates have multiple sections, "
                      u"each identified by a string. When the "
                      u"campaign is created, we need to know where to "
                      u"put the dynamically created newsletter content."),
        default=u"std_content00",
        required=True,
        )

    subject = schema.TextLine(
        title=_(u"Subject"),
        description=_(u"The newsletter subject."),
        required=False,
        default=u"",
        )

    start = schema.Date(
        title=_(u"Start date"),
        description=_(u"Include items published after this date."),
        required=False,
        default=None,
        )

    image = schema.TextLine(
        title=_(u"Image field"),
        description=_(u"The name of the content field that contains "
                      u"the content lead image. Note that it does not "
                      u"need to exist for all content."),
        required=False,
        default=u"image",
        )

    scale = schema.TextLine(
        title=_(u"Image scale"),
        description=_(u"The name of the image scale."),
        required=False,
        default=u"thumb",
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

    description = schema.Text(
        title=_(u"Description"),
        description=_(u"Enter a description of your newsletter."),
        required=False,
        default=u"Join our newsletter and stay updated!",
        )


class IControlPanel(IFeedSettings):
    urls = schema.Tuple(
        title=_(u"RSS"),
        description=_(u"This field lists an RSS-feed for each of "
                      u"the available feed strings (including "
                      u"those that are automatically pulled from "
                      u"interest groups."),
        required=False,
        value_type=schema.ASCIILine(),
        )

    lists = schema.Tuple(
        title=_(u"Lists"),
        description=_(u"This listing shows a link to a "
                      u"subscription form for each of the defined "
                      u"lists in your account."),
        required=False,
        value_type=schema.ASCIILine(),
        )


class IFeedControl(Interface):
    """Feed control settings."""

    feeds = schema.Set(
        title=_(u"Feeds"),
        description=_(u"Select one or more items from this list "
                      u"to include in the corresponding feed."),
        required=False,
        value_type=schema.Choice(
            vocabulary="collective.chimpfeed.vocabularies.Feeds",
            )
        )

    feedCategory = schema.Choice(
        title=_(u"Feed category"),
        description=_(u"Please select a category for this item."),
        required=False,
        default=None,
        vocabulary="collective.chimpfeed.vocabularies.Categories",
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

