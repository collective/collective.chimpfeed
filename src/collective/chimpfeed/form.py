import os
import re
import time
import datetime
import math
import greatape
import cgi
import urllib
import pprint

from Products.statusmessages.interfaces import IStatusMessage
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.i18nl10n import ulocalized_time
from Products.CMFPlone.interfaces import IPloneSiteRoot

from Acquisition import Implicit, ImplicitAcquisitionWrapper
from ComputedAttribute import ComputedAttribute
from zExceptions import BadRequest

from ZODB.utils import u64
from DateTime import DateTime

from plone.memoize.ram import cache
from plone.memoize import view
from plone.memoize.instance import memoizedproperty
from plone.memoize.volatile import DontCache
from plone.memoize.forever import memoize as forever
from plone.z3cform.layout import wrap_form

from zope.i18n import negotiate
from zope.i18n import translate
from zope.i18n.interfaces import ITranslationDomain
from zope.component import queryUtility, getUtility, getMultiAdapter
from zope.interface import alsoProvides
from zope.interface import Interface
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm
from zope.schema import ValidationError
from zope import schema
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.widget import SequenceWidget
from z3c.form.widget import FieldWidget
from z3c.form.interfaces import IErrorViewSnippet
from z3c.form.interfaces import IActions
from z3c.form.interfaces import IWidgets
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.browser.checkbox import SingleCheckBoxFieldWidget
from z3c.form.interfaces import IWidget
from z3c.form.interfaces import HIDDEN_MODE

try:
    from z3c.form.interfaces import NO_VALUE
except ImportError:
    from z3c.form.interfaces import NOVALUE as NO_VALUE

from collective.chimpfeed import MessageFactory as _
from collective.chimpfeed import logger
from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed.interfaces import INameSplitter
from collective.chimpfeed.interfaces import ICampaignPortlet
from collective.chimpfeed.interfaces import INewsletterPortlet
from collective.chimpfeed.interfaces import ISubscriptionFormSettings
from collective.chimpfeed.interfaces import IApiUtility
from collective.chimpfeed.vocabularies import interest_groups_factory
from collective.chimpfeed.vocabularies import InterestGroupVocabulary
from collective.chimpfeed.splitters import GenericNameSplitter

re_email = re.compile(r"^(\w&.%#$&'\*+-/=?^_`{}|~]+!)*[\w&.%#$&'\*+-/=?^_"
                      r"`{}|~]+@(([0-9a-z]([0-9a-z-]*[0-9a-z])?\.)+[a-z]{2,6}"
                      r"|([0-9]{1,3}\.){3}[0-9]{1,3})$", re.IGNORECASE)


def create_groupings(groups):
    groupings = {}
    for grouping_id, name, interest_id in groups:
        groupings.setdefault(grouping_id, []).append(name)
    return groupings


def cache_on_get_for_an_hour(method, self):
    if self.request['REQUEST_METHOD'] != 'GET':
        raise DontCache

    return (
        time.time() // (60 * 60),
        self.id,
        self.request.get('list_id'),
        self.request.get('success')
    )


def is_email(value):
    if re_email.match(value):
        return True

    raise EmailValidationError(value)


class EmailValidationError(ValidationError):
    __doc__ = _(u"Not a valid e-mail address.")


class ICampaign(ICampaignPortlet):
    """Note that most fields are inherited from the portlet."""

    limit = schema.Bool(
        title=_(u"Limit"),
        description=_(u"Include scheduled items up until today's date only."),
        default=True,
        required=False,
    )

    filtering = schema.Bool(
        title=_(u"Apply filtering markup"),
        description=_(u"Select this option to apply the markup "
                      u"required for automatic interest group "
                      u"filtering."),
        default=True,
        required=False,
    )

    create_draft = schema.Bool(
        title=_(u"Create new campaigns as drafts"),
        required=False,
        default=True
    )

    schedule = schema.Datetime(
        title=_(u"Schedule date"),
        description=_(u"If provided, item will be scheduled to be sent "
                      u"at this time."),
        required=False,
        default=None,
    )


class INewsletter(INewsletterPortlet):
    """Note that most fields are inherited from the portlet."""

    interests = schema.Tuple(
        title=_(u"Select interest groups"),
        description=_(u"If no interest groups are selected the predefined "
                      u"groups will be used, which were specified during the "
                      u"creation of the portlet"),
        value_type=schema.Choice(
            vocabulary="collective.chimpfeed.vocabularies.InterestGroups",
        ),
        required=False,
    )

    create_draft = schema.Bool(
        title=_(u"Create new campaigns as drafts"),
        required=False,
        default=True
    )

    schedule = schema.Datetime(
        title=_(u"Schedule date"),
        description=_(u"If provided, item will be scheduled to be sent "
                      u"at this time."),
        required=False,
        default=None,
    )


class IModeration(Interface):
    items = schema.Tuple(
        value_type=schema.Choice(
            vocabulary="collective.chimpfeed.vocabularies.ScheduledItems",
        ),
        required=False,
    )


class ISubscription(Interface):
    email = schema.TextLine(
        title=_(u"E-mail"),
        required=True,
        constraint=is_email,
    )

    interests = schema.Tuple(
        value_type=schema.Choice(
            vocabulary="collective.chimpfeed.vocabularies.InterestGroups",
        ),
        required=False,
    )


class ModerationWidget(SequenceWidget):
    template = ViewPageTemplateFile("moderate.pt")

    @classmethod
    def factory(cls, field, request):
        return FieldWidget(field, cls(request))

    def render(self):
        return self.template()

    def _localize_time(self, time, long_format):
        util = getToolByName(self.context, 'translation_service')

        return util.ulocalized_time(
            time, long_format=long_format,
            context=self.context, request=self.request,
            domain='plonelocales'
        ).lstrip('0')

    @memoizedproperty
    def entries(self):
        entries = []
        catalog = self.context.portal_catalog

        for term in self.terms:
            rid = term.value
            entry = catalog.getMetadataForRID(rid)
            date = entry['feedSchedule']
            if date is not None:
                # Must be a `DateTime`, even for Dexterity-based
                # content.
                if isinstance(date, DateTime):
                    entry['id'] = rid
                    entries.append(entry)

        return entries

    @memoizedproperty
    def action_required(self):
        for entry in self.entries:
            if not entry['feedModerate']:
                return True

    @property
    def groups(self):
        last = None
        groups = []
        entries = []
        today = DateTime()
        today = DateTime(today.year(), today.month(), today.day())

        for entry in self.entries:
            date = entry['feedSchedule']
            days = int(math.floor(date - today))
            if days != last:
                entries = []

                # To-Do: Use Plone's date formatters
                if days == -1:
                    name = _(u"Today")
                else:
                    abbr = date.strftime("%a")
                    name = translate(
                        'weekday_%s' % abbr.lower(),
                        domain="plonelocales",
                        context=self.request
                    ).capitalize()

                    if days < 0 or days >= 7:
                        name = _(u"${subject} ${date}", mapping={
                            'subject': name,
                            'date': self._localize_time(date, False),
                        })

                groups.append({
                    'date': name,
                    'entries': entries,
                })

            last = days
            entries.append(entry)

        return groups


class InterestsWidget(SequenceWidget):
    template = ViewPageTemplateFile("interests.pt")

    @cache(cache_on_get_for_an_hour)
    def render(self):
        return self.template()

    @classmethod
    def factory(cls, field, request):
        return FieldWidget(field, cls(request))

    @property
    def vocabulary(self):
        settings = IFeedSettings(self.context)
        return ImplicitAcquisitionWrapper(
            interest_groups_factory, settings)

    @memoizedproperty
    def groupings(self):
        utility = getUtility(IApiUtility, context=self.context)
        wrapped = utility.__of__(self.context)
        return tuple(wrapped.get_groupings())

    def renderInterestGroups(self):
        groups = create_groupings(self.context.interest_groups)

        terms = []
        for grouping in self.groupings:
            grouping_id = grouping['id']
            names = groups.get(grouping_id, ())
            for group in grouping['groups']:
                name = group['name']
                if name in names:
                    terms.append(self.vocabulary.get_term_for_group(
                        group, grouping
                    ))

        return self.renderChoices(terms)

    def renderInterestGroupings(self):
        filtered = (
            grouping for grouping in self.groupings
            if grouping['id'] in self.context.interest_groupings
        )

        rendered = []

        for grouping in filtered:
            terms = tuple(self.vocabulary.get_terms_for_grouping(
                grouping
            ))

            # Create label from the grouping name
            label = cgi.escape(grouping['name'])
            result = self.renderChoices(terms, label, grouping['id'])
            rendered.append(result)

        return u"\n".join(rendered)

    def renderChoices(self, terms, label=None, grouping_id=None):
        choice = schema.Choice(
            vocabulary=SimpleVocabulary(terms),
        )

        field = self.field.bind(self.context)
        field.value_type = choice

        widget = CheckBoxFieldWidget(field, self.request)
        widget.mode = self.mode
        widget.name = self.name
        widget.id = self.id

        if grouping_id is not None:
            widget.id += "-%s" % grouping_id

        widget.update()
        result = widget.render()

        if label is not None and self.mode != HIDDEN_MODE:
            result = (
                u'<fieldset class="interest-group">'
                u'<legend>%s</legend>%s</fieldset>') % (label, result)

        return result


class SchemaErrorSnippet(object):
    implements(IErrorViewSnippet)

    def __init__(self, error, request, widget, field, form, content):
        self.error = error
        self.widget = widget
        self.message = error.__doc__

    def update(self):
        pass

    def render(self):
        return _(self.error.__doc__)


class BaseForm(form.Form):
    ignoreContext = True

    @property
    def prefix(self):
        # Make sure form prefix is unique
        return 'form-%d-%d.' % (
            u64(self.context._p_oid),
            int(self.context._p_mtime) % 10000
        )


class BaseCampaignForm(BaseForm):
    def createCampaign(self, api_key, method, subject,
                       create_draft, schedule, rendered, next_url,
                       segment_opts={}):
        try:
            if not rendered.strip():
                IStatusMessage(self.request).addStatusMessage(
                    _(u"No content found; newsletter not created."),
                    "info"
                )

                return

            if api_key:
                api = greatape.MailChimp(api_key, debug=False)

                try:
                    for entry in api(method="lists"):
                        if entry['id'] == self.context.mailinglist:
                            break
                    else:
                        IStatusMessage(self.request).addStatusMessage(
                            _(u"Mailinglist not found."),
                            "error"
                        )

                        return

                    if self.context.template:
                        section = 'html_%s' % self.context.section
                    else:
                        section = 'html'

                    args = {}

                    args['method'] = method
                    args['type'] = 'regular'
                    args['content'] = {section: rendered}
                    if segment_opts:
                        args['segment_opts'] = segment_opts

                    options = {}
                    options['subject'] = subject.encode("utf-8") or \
                        entry['default_subject']
                    options['from_email'] = entry['default_from_email']
                    options['from_name'] = \
                        entry['default_from_name'].encode("utf-8")
                    options['to_email'] = 0
                    options['list_id'] = self.context.mailinglist
                    options['template_id'] = self.context.template or None
                    options['generate_text'] = True

                    args['options'] = options

                    result = api(**args)

                    if result:
                        if not create_draft:
                            if schedule:
                                # Apply local time zone to get GMT
                                schedule = schedule + datetime.timedelta(
                                    seconds=time.timezone
                                )

                                # Format time
                                schedule_time = time.strftime(
                                    "%Y-%m-%d %H:%M:%S", schedule.utctimetuple()
                                )

                                schedule = api(
                                    method="campaignSchedule",
                                    cid=result,
                                    schedule_time=schedule_time,
                                )

                                if not schedule:
                                    IStatusMessage(self.request).addStatusMessage(
                                        _(u"Campaign created, but not scheduled."),
                                        "error"
                                    )

                                    return
                            else:
                                api(method="campaignSendNow",
                                    cid=result)

                        next_url = self.context.portal_url() + \
                            "/@@chimpfeed-content?cid=%s" % result

                except greatape.MailChimpError, exc:
                    IStatusMessage(self.request).addStatusMessage(
                        _(u"Unable to process request: ${message}",
                          mapping={'message': exc.msg}), "error"
                    )
                    logger.warn(exc.msg)
                    logger.warn(pprint.pformat(args))
                    return

                return bool(result)
        finally:
            self.request.response.redirect(next_url)


class CampaignForm(BaseCampaignForm):
    fields = field.Fields(
        ICampaign['start'],
        ICampaign['limit'],
        ICampaign['filtering'],
        ICampaign['subject'],
        ICampaign['create_draft'],
        ICampaign['schedule'],
    )

    fields['limit'].widgetFactory = SingleCheckBoxFieldWidget
    fields['filtering'].widgetFactory = SingleCheckBoxFieldWidget
    fields['create_draft'].widgetFactory = SingleCheckBoxFieldWidget

    ignoreContext = True

    @button.buttonAndHandler(_(u'Preview'))
    def handlePreview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        url = self.context.aq_parent.absolute_url()
        params = self.makeParams(**data)
        return self.request.response.redirect(
            url + "/@@chimpfeed-preview?%s" % urllib.urlencode(params))

    def makeParams(self, start=None, limit=False,
                   filtering=False, **extra):
        today = datetime.datetime.now()

        return dict(
            start=start.isoformat(),
            filtering=filtering and '1' or "",
            until=limit and today.isoformat() or "",
            image=self.context.image,
            scale=self.context.scale,
        )

    @button.buttonAndHandler(_(u'Create'))
    def handleCreate(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        success = self.process("campaignCreate", **data)

        if success:
            IStatusMessage(self.request).addStatusMessage(
                _(u"Campaign created."),
                "info"
            )

            # Set date to tomorrow's date.
            self.context.start = datetime.date.today() + \
                datetime.timedelta(days=1)

    def process(self, method, subject=None,
                create_draft=False, schedule=None, **data):
        settings = IFeedSettings(self.context)
        api_key = settings.mailchimp_api_key

        view = getMultiAdapter(
            (self.context.aq_parent, self.request), name="chimpfeed-campaign"
        )

        params = self.makeParams(**data)
        rendered = view.template(**params).encode('utf-8')
        next_url = self.request.get('HTTP_REFERER') or self.action

        segments = view.getSegments(**params).items()
        if segments:
            segment_opts = {
                'match': 'all',
                'conditions':
                [{'field': 'interests-%s' % groupingid,
                  'op':'one',
                  'value': groupids}
                 for groupingid, groupids in segments[:10]
                 ]}

            if len(segments) > 10:
                count = len(segments) - 10
                IStatusMessage(self.request).addStatusMessage(
                    _(u"%d segments were ignored "
                      u"(Mailchimp limits this to 10)." % count),
                    "warning"
                )
        else:
            segment_opts = {}

        return self.createCampaign(api_key, method, subject, create_draft,
                                   schedule, rendered, next_url, segment_opts)

    def update(self):
        super(CampaignForm, self).update()

        today = datetime.date.today()

        date = self.context.start
        if date is None:
            date = today

        start = self.widgets['start']
        start.value = (date.year, date.month, date.day)

        subject = self.widgets['subject']
        if not subject.value:
            value = self.context.subject or \
                self.context.Title().decode('utf-8')

            subject.value = _(
                u"${subject} ${date}", mapping={
                'subject': value, 'date': ulocalized_time(
                    DateTime(),
                    context=self.context,
                    request=self.request
                ).lstrip('0')}
            )

class NewsletterForm(BaseCampaignForm):
    fields = field.Fields(
        INewsletter['subject'],
        INewsletter['interests'],
        INewsletter['schedule'],
        INewsletter['create_draft'],
    )

    fields['create_draft'].widgetFactory = SingleCheckBoxFieldWidget
    fields['interests'].widgetFactory = CheckBoxFieldWidget

    ignoreContext = True

    def getSegmentConditions(self, interest_groups):
        if not interest_groups and hasattr(self.context, 'interest_groups'):
            interest_groups = self.context.interest_groups
        if not interest_groups:
            return []

        (grouping_id, interest_description, group_id) = interest_groups[0]

        return [{'field': 'interests-' + str(grouping_id),
                 'op': 'one',
                 'value': ','.join([interest[1].encode("utf-8")
                                    for interest
                                    in interest_groups])
                 }]

    @button.buttonAndHandler(_(u'Preview'))
    def handlePreview(self, action):
        if self.context.REQUEST.get('restricted_traverse', False):
            return

        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        url = self.context.aq_parent.absolute_url()
        return self.request.response.redirect(
            url + "/@@chimpfeed-newsletter-content")

    @button.buttonAndHandler(_(u'Create'))
    def handleCreate(self, action):
        if self.context.REQUEST.get('restricted_traverse', False):
            return

        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        if not self.context.select_interest_groups:
            data.update(dict(interests=self.context.interest_groups))
        success = self.process("campaignCreate", **data)

        if success:
            IStatusMessage(self.request).addStatusMessage(
                _(u"Campaign created."),
                "info"
            )

    def process(self, method, subject=None,
                create_draft=False, schedule=None, interests=None,
                **data):
        settings = IFeedSettings(self.context)
        api_key = settings.mailchimp_api_key

        view = getMultiAdapter(
            (self.context.aq_parent, self.request),
            name="chimpfeed-newsletter-campaign"
        )

        rendered = view.template().encode('utf-8')
        next_url = self.request.get('HTTP_REFERER') or self.action
        segment_conditions = self.getSegmentConditions(interests)

        return self.createCampaign(
            api_key, method, subject,
            create_draft, schedule, rendered, next_url,
            segment_conditions and {
                'match': 'all',
                'conditions': segment_conditions
            } or None
        )

    def update(self):
        super(NewsletterForm, self).update()

        today = datetime.date.today()

        subject = self.widgets['subject']
        if not subject.value:
            value = self.context.subject or \
                self.context.Title().decode('utf-8')

            subject.value = _(
                u"${subject} ${date}", mapping={
                'subject': value, 'date': ulocalized_time(
                    DateTime(),
                    context=self.context,
                    request=self.request
                ).lstrip('0')}
            )

        if not self.context.select_interest_groups:
            self.widgets['interests'].mode = HIDDEN_MODE

    def render(self):
        if self.context.REQUEST.get('restricted_traverse', False):
            return ''
        return BaseCampaignForm.render(self)


class ModerationForm(BaseForm):
    fields = field.Fields(IModeration)

    fields['items'].widgetFactory = ModerationWidget.factory

    ignoreContext = True

    @button.buttonAndHandler(_(u'Approve'))
    def handleApprove(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        catalog = self.context.portal_catalog
        bumped = []
        today = datetime.date.today()

        uids = []
        for rid in data['items'] or ():
            metadata = catalog.getMetadataForRID(rid)
            uids.append(metadata['UID'])

        settings = IFeedSettings(self.context)

        brains = catalog.unrestrictedSearchResults(UID=uids)
        for brain in brains:
            obj = brain.getObject()

            # Bump the scheduled date to today's date. This ensures that
            # the item will be shown on the moderation portlet.
            try:
                date = obj.getField('feedSchedule').get(obj)
                if date is not None:
                    date = date.asdatetime().date()
            except AttributeError:
                date = obj.feedSchedule

            if settings.bump_date_on_moderation and (date is None or date < today):
                try:
                    field = obj.getField('feedSchedule')
                except AttributeError:
                    obj.feedSchedule = today
                else:
                    field.set(obj, DateTime(
                        today.year, today.month, today.day
                    ))

                bumped.append(obj)

            try:
                field = obj.getField('feedModerate')
            except AttributeError:
                obj.feedModerate = True
            else:
                field.set(obj, True)

            # Reindex entire object (to make sure the metadata is
            # updated, too).
            obj.reindexObject()

        if data['items']:
            self.widgets['items'].update()

        if bumped:
            IStatusMessage(self.request).addStatusMessage(
                _(u"The scheduled date has been set to today's date "
                  u"for the following items that were scheduled to "
                  u"a date in the past: ${titles}.",
                  mapping={'titles': u', '.join(
                      [obj.Title().decode('utf-8') for obj in bumped])}),
                "info",
            )

    def update(self):
        super(ModerationForm, self).update()

        # No reason to show a button if no action is required (or
        # possible).
        if not self.widgets['items'].action_required:
            del self.actions['approve']


class SubscribeContext(Implicit):
    interest_groups = ()

    def __init__(self, request):
        list_id = self.mailinglist = request['list_id']
        self.factory = InterestGroupVocabulary(list_id)

    def get_name(self):
        api = getUtility(IApiUtility, context=self)
        for list_id, name in api.get_lists():
            if list_id == self.mailinglist:
                return name

        return _(u"Untitled")

    name = ComputedAttribute(get_name, 1)

    def get_interest_groupings(self):
        vocabulary = self.factory(self)
        return set(
            term.value[0] for term in vocabulary
        )

    interest_groupings = ComputedAttribute(get_interest_groupings, 1)


class SubscribeForm(BaseForm):

    @property
    def fields(self):
        fields = field.Fields()
        settings = IFeedSettings(self.context)
        if settings.show_name:
            fields += field.Fields(
                schema.TextLine(
                    __name__="name",
                    title=_(u"Name"),
                    required=False,
                )
            )
        fields += field.Fields(ISubscription)
        fields['interests'].widgetFactory = InterestsWidget.factory
        return fields

    @button.buttonAndHandler(_(u'Register'))
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        settings = IFeedSettings(self.context)
        api_key = settings.mailchimp_api_key
        next_url = self.nextURL()

        try:
            list_id = (
                data.pop('list_id', None) or
                self.getContent().mailinglist
            )
            try:
                name = data.pop('name')
            except KeyError:
                name = ''
            email = data.pop('email')
            interests = data.pop('interests')

            content = self.getContent()

            preselected = getattr(content, 'preselected_interest_groups', None)
            if preselected:
                if not interests:
                    interests = preselected
                else:
                    interests = interests + preselected

            if api_key:
                api = greatape.MailChimp(api_key, debug=False)

                # Negotiate language
                language = negotiate(self.request)

                # Split full name into first (given) and last name.
                try:
                    fname, lname = queryUtility(
                        INameSplitter, name=language,
                        default=GenericNameSplitter
                        ).split_name(name)
                except AttributeError:
                    fname, lname = u'', u''

                # Log subscription attempt.
                logger.info(("listSubscribe(%r, %r, %r, %r)" % (
                    list_id, email, fname, lname)).encode('utf-8'))

                merge_vars = {
                    'FNAME': fname.encode('utf-8'),
                    'LNAME': lname.encode('utf-8'),
                    'GROUPINGS': [
                        dict(
                            id=grouping_id,
                            groups=",".join(
                                group.
                                encode('utf-8').
                                replace(',', '\\,')
                                for group in group_names
                            ),
                        )
                        for (grouping_id, group_names) in
                        create_groupings(interests).items()
                    ]
                }

                for name, value in data.items():
                    if value is not None:
                        merge_vars[name.upper()] = value.encode('utf-8')

                try:
                    result = api(
                        method="listSubscribe", id=list_id,
                        email_address=email,
                        update_existing=True,
                        replace_interests=False,
                        merge_vars=merge_vars
                    )
                except greatape.MailChimpError, exc:
                    logger.warn(exc.msg)

                    # ... is not a valid interest grouping id for the list
                    if exc.code == 270:
                        return IStatusMessage(self.request).addStatusMessage(
                            _(u"There was a problem signing you up for "
                              u"the selected interest groups. This could "
                              u"mean that the subscription service is "
                              u"configured incorrectly. Please contact "
                              u"the webmaster."),
                            "error",
                        )
                else:
                    if result:
                        next_url += ('?' in next_url
                                     and '&' or '?') + 'success=yes'

                        return IStatusMessage(self.request).addStatusMessage(
                            _(u"Thank you for signing up. We'll send you a "
                              u"confirmation message by e-mail shortly."),
                            "info"
                        )

            IStatusMessage(self.request).addStatusMessage(
                _(u"An error occurred while processing your "
                  u"request to sign up for ${email}. "
                  u"Please try again!", mapping={'email': email}),
                "error")

        finally:
            self.request.response.redirect(next_url)

    def nextURL(self):
        return self.action


class JavascriptWidget(field.Field):
    """Generic javascript snippet."""

    error = None
    required = False

    def __call__(self, field, request):
        widget = type(self)(field)
        widget.request = request
        alsoProvides(widget, IWidget)
        return widget

    def get(self, mode):
        return self

    @property
    def widgetFactory(self):
        return self

    def render(self):
        return u'<script type="text/javascript">\n' + \
               self.body + \
               u'</script>'

    def update(self):
        assert self.mode == HIDDEN_MODE

    def extract(self):
        return NO_VALUE


class SelectAllGroupsJavascript(JavascriptWidget):
    """Replace the fieldset legend with a select all checkbox."""

    path = os.path.join(os.path.dirname(__file__), "select.js")

    @property
    @forever
    def body(self):
        body = open(self.path, 'rb').read()

        # Extract and translate strings by heuristic:
        td = getUtility(ITranslationDomain, name="collective.chimpfeed")
        for string in re.compile(r'>([\w\s]+)<').findall(body):
            msg_id = string.decode('utf-8')
            translation = td.translate(msg_id, context=self.request)
            body = body.replace(string, translation)

        return body


class ListSubscribeForm(SubscribeForm):
    @property
    def fields(self):
        fields = field.Fields()
        settings = IFeedSettings(self.context)

        # Javascript-widget
        if settings.enable_select_all:
            fields += field.Fields(SelectAllGroupsJavascript(schema.Field(
                __name__="js", required=False), mode="hidden"))

        # Include form fields, but change the order around.
        fields += field.Fields(ISubscription).select('interests')
        fields['interests'].widgetFactory = InterestsWidget.factory

        if settings.show_name:
            fields += field.Fields(
                schema.TextLine(
                    __name__="name",
                    title=_(u"Name"),
                    required=False,
                )
            )

        fields += field.Fields(ISubscription).select('email')

        # Add mailinglist as hidden field
        fields += field.Fields(schema.ASCII(
            __name__="list_id",
            required=True),
            mode="hidden"
        )

        context = self.getContent()
        api = getUtility(IApiUtility, context=self.context)
        result = api.list_merge_vars(context.mailinglist)

        for entry in result:
            name = entry['tag'].lower()

            if name in fields:
                continue

            if not entry['show']:
                continue

            # Skip all-uppercase:
            if entry['name'] == entry['name'].upper():
                continue

            field_type = entry['field_type']
            required = entry['req']

            if field_type == 'text':
                factory = schema.TextLine
                options = {}

            elif field_type == 'dropdown':
                factory = schema.Choice
                choices = list(entry['choices'])

                if not required:
                    choices.append(u"")
                    required = True

                options = {
                    'vocabulary': SimpleVocabulary([
                        SimpleTerm(value=value,
                                   token=value.encode(
                                       'ascii',
                                       'xmlcharrefreplace'),
                                   title=value or _(u"None"))
                        for value in choices])
                }

            else:
                continue

            fields += field.Fields(factory(
                __name__=name.encode('utf-8'),
                default=entry['default'],
                required=required,
                title=_(entry['name']),
                **options
            ))

        return fields

    # Remove prefix; we want to be able to provide defaults using a
    # simple format.
    prefix = ""

    @property
    def description(self):
        context = self.context.aq_base
        if self.request.get('success'):
            return u''
        elif not IPloneSiteRoot.providedBy(context) \
                 and context.Description():
            return context.Description()
        else:
            return _(u"Select subscription options and submit form.")

    @property
    def label(self):
        if self.request.get('success'):
            return _(u"Request processed")

        name = self.getContent().name
        return _(u"Subscribe to: ${name}", mapping={'name': name})

    @view.memoize
    def getContent(self):
        if ISubscriptionFormSettings.providedBy(self.context):
            return self.context

        settings = IFeedSettings(self.context)
        try:
            context = SubscribeContext(self.request)
        except KeyError, exc:
            raise BadRequest(u"Missing parameter: %s." % exc)

        return context.__of__(
            ImplicitAcquisitionWrapper(
                settings, self.context)
        )

    def nextURL(self):
        list_id = self.request.get('list_id', '')
        return self.action + "?list_id=%s" % list_id

    def updateActions(self):
        self.actions = getMultiAdapter(
            (self, self.request, self.getContent()), IActions)

        self.actions.update()

        if self.request.get('success'):
            for name in self.actions:
                del self.actions[name]

    def updateWidgets(self):
        self.widgets = getMultiAdapter(
            (self, self.request, self.getContent()), IWidgets
        )

        if self.request.get('success'):
            mode = HIDDEN_MODE

            for name, widget in self.widgets.items():
                if isinstance(widget, JavascriptWidget):
                    del self.widgets[name]
        else:
            mode = self.mode

        self.widgets.mode = mode
        self.widgets.prefix = ""
        self.widgets.ignoreContext = self.ignoreContext
        self.widgets.ignoreRequest = self.ignoreRequest
        self.widgets.ignoreReadonly = self.ignoreReadonly
        self.widgets.update()

ListSubscribeFormView = wrap_form(ListSubscribeForm)


class ListSubscribeFormFieldWidgets(field.FieldWidgets):
    prefix = ""
