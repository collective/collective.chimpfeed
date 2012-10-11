import os
import re
import time
import datetime
import math
import greatape
import cgi
import urllib

from Products.statusmessages.interfaces import IStatusMessage
from Products.CMFCore.utils import getToolByName
from Acquisition import Implicit, ImplicitAcquisitionWrapper
from ComputedAttribute import ComputedAttribute
from zExceptions import BadRequest

from ZODB.utils import u64
from DateTime import DateTime

from plone.memoize.ram import cache
from plone.memoize import view
from plone.memoize.instance import memoizedproperty
from plone.memoize.volatile import DontCache

from plone.z3cform.layout import wrap_form

from zope.i18n import negotiate
from zope.i18n import translate
from zope.component import queryUtility, getUtility, getMultiAdapter
from zope.interface import alsoProvides
from zope.interface import Interface
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema import ValidationError
from zope import schema
from zope.app.component.hooks import getSite
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.widget import SequenceWidget
from z3c.form.widget import FieldWidget
from z3c.form.interfaces import IErrorViewSnippet
from z3c.form.interfaces import IWidgets
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.interfaces import IWidget

try:
    from z3c.form.interfaces import NO_VALUE
except ImportError:
    from z3c.form.interfaces import NOVALUE as NO_VALUE

from collective.chimpfeed import MessageFactory as _
from collective.chimpfeed import logger
from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed.interfaces import INameSplitter
from collective.chimpfeed.interfaces import ICampaignPortlet
from collective.chimpfeed.interfaces import ISubscriptionFormSettings
from collective.chimpfeed.interfaces import IApiUtility
from collective.chimpfeed.vocabularies import interest_groups_factory
from collective.chimpfeed.vocabularies import InterestGroupVocabulary
from collective.chimpfeed.splitters import GenericNameSplitter


re_email = re.compile(r"^(\w&.%#$&'\*+-/=?^_`{}|~]+!)*[\w&.%#$&'\*+-/=?^_`{}|~]+@(([0-9a-z]([0-9a-z-]*[0-9a-z])?\.)+[a-z]{2,6}|([0-9]{1,3}\.){3}[0-9]{1,3})$", re.IGNORECASE)


def create_groupings(groups):
    groupings = {}
    for grouping_id, name in groups:
        groupings.setdefault(grouping_id, []).append(name)
    return groupings


def cache_on_get_for_an_hour(method, self):
    if self.request['REQUEST_METHOD'] != 'GET':
        raise DontCache

    return time.time() // (60 * 60), self.id, self.request.get('list_id')


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
    name = schema.TextLine(
        title=_(u"Name"),
        required=True,
        )

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
            )

    @memoizedproperty
    def entries(self):
        entries = []
        catalog = self.context.portal_catalog

        for term in self.terms:
            rid = term.value
            entry = catalog.getMetadataForRID(rid)
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

        for entry in self.entries:
            date = entry['feedSchedule']
            if date is None:
                continue
            days = int(math.floor(date - today))
            if days != last:
                entries = []

                # To-Do: Use Plone's date formatters
                if days == -1:
                    name = _(u"Today")
                elif days < 0 or days >= 7:
                    name = self._localize_time(date, False)
                else:
                    abbr = date.strftime("%a")
                    name = translate(
                        'weekday_%s' % abbr.lower(),
                        domain="plonelocales",
                        context=self.request
                        )

                groups.append({
                    'date': name,
                    'entries': entries,
                    })

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
        site = getSite()
        utility = getUtility(IApiUtility, context=site)
        return tuple(utility.get_groupings())

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
        widget.name = self.name
        widget.id = self.id

        if grouping_id is not None:
            widget.id += "-%s" % grouping_id

        widget.update()
        result = widget.render()

        if label is not None:
            result = (
                u'<fieldset class="interest-group">'
                u'<legend>%s</legend>%s</fieldset>') % (
                label, result
                )

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


class CampaignForm(BaseForm):
    fields = field.Fields(
        ICampaign['start'],
        ICampaign['subject'],
        ICampaign['schedule'],
        )

    ignoreContext = True

    @button.buttonAndHandler(_(u'Preview'))
    def handlePreview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        url = self.context.portal_url()

        return self.request.response.redirect(
            url + "/@@chimpfeed-preview?%s" % urllib.urlencode({
                'start': data['start'].isoformat(),
                'image': self.context.image,
                'scale': self.context.scale
                }))

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

    def process(self, method, subject=None, start=None,
                limit=False, schedule=None):
        settings = IFeedSettings(self.context)
        api_key = settings.mailchimp_api_key

        site = self.context.portal_url.getPortalObject()
        view = site.restrictedTraverse('chimpfeed-campaign')

        today = datetime.date.today()

        if limit:
            until = today.isoformat()
        else:
            until = None

        rendered = view.template(
            start=start.isoformat(),
            until=until,
            image=self.context.image,
            scale=self.context.scale,
            ).encode('utf-8')

        next_url = self.request.get('HTTP_REFERER') or self.action

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

                    result = api(
                        method=method,
                        type="regular",
                        options={
                            'subject': subject or entry['default_subject'],
                            'from_email': entry['default_from_email'],
                            'from_name': entry['default_from_name'],
                            'to_email': 0,
                            'list_id': self.context.mailinglist,
                            'template_id': self.context.template or None,
                            'generate_text': True,
                            },
                        content={
                            section: rendered,
                            },
                        )

                    if result:
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

                        next_url = self.context.portal_url() + \
                                   "/@@chimpfeed-content?cid=%s" % result

                except greatape.MailChimpError, exc:
                    IStatusMessage(self.request).addStatusMessage(
                        _(u"Unable to process request."), "error"
                        )
                    logger.warn(exc.msg)
                    return

                return bool(result)
        finally:
            self.request.response.redirect(next_url)

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
            subject.value = self.context.subject or \
                            self.context.Title().decode('utf-8')

        schedule = self.widgets['schedule']
        assert isinstance(schedule.value, tuple)

        if not schedule.value[0]:
            tomorrow = today + datetime.timedelta(days=1)

            schedule.value = (
                tomorrow.year, tomorrow.month, tomorrow.day, "09", "00"
                )


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

        for rid in data['items'] or ():
            metadata = catalog.getMetadataForRID(rid)
            for brain in catalog(UID=metadata['UID']):
                obj = brain.getObject()

                try:
                    field = obj.getField('feedModerate')
                except AttributeError:
                    obj.feedModerate = True
                else:
                    field.set(obj, True)

                # Bump the scheduled date to today's date. This ensures that
                # the item will be shown on the moderation portlet.
                try:
                    date = obj.getField('feedSchedule').get(obj)
                    if date is not None:
                        date = date.asdatetime().date()
                except AttributeError:
                    date = obj.feedSchedule

                if date is not None or date < today:
                    try:
                        field = obj.getField('feedSchedule')
                    except AttributeError:
                        obj.feedSchedule = today
                    else:
                        field.set(obj, DateTime(
                            today.year, today.month, today.day
                            ))

                    bumped.append(obj)

                # Reindex entire object (to make sure the metadata is
                # updated, too).
                obj.reindexObject()

        if bumped:
            IStatusMessage(self.request).addStatusMessage(
                _(u"The scheduled date has been set to today's date "
                  u"for the following items that were scheduled to "
                  u"a date in the past: ${titles}.",
                  mapping={'titles': u', '.join(
                      [obj.Title() for obj in bumped])}),
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
    fields = field.Fields(ISubscription)

    fields['interests'].widgetFactory = InterestsWidget.factory

    @button.buttonAndHandler(_(u'Register'))
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        settings = IFeedSettings(self.context)
        api_key = settings.mailchimp_api_key
        next_url = self.nextURL()
        content = self.getContent()

        try:
            list_id = content.mailinglist

            email = data['email']
            name = data['name']
            interests = data['interests']

            if api_key:
                api = greatape.MailChimp(api_key, debug=False)

                # Negotiate language
                language = negotiate(self.request)

                # Split full name into first (given) and last name.
                fname, lname = queryUtility(
                    INameSplitter, name=language, default=GenericNameSplitter
                    ).split_name(name)

                # Log subscription attempt.
                logger.info(("listSubscribe(%r, %r, %r, %r)" % (
                    list_id, email, fname, lname)).encode('utf-8'))

                try:
                    result = api(
                        method="listSubscribe", id=list_id,
                        email_address=email,
                        update_existing=True,
                        replace_interests=False,
                        merge_vars={
                            'FNAME': fname.encode('utf-8'),
                            'LNAME': lname.encode('utf-8'),
                            'GROUPINGS': [
                                dict(
                                    id=grouping_id,
                                    groups=",".join(
                                        group.\
                                        encode('utf-8').\
                                        replace(',', '\\,')
                                        for group in group_names
                                        ),
                                    )
                                for (grouping_id, group_names) in
                                create_groupings(interests).items()
                                ]
                            },
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
        pass

    def extract(self):
        return NO_VALUE


class SelectAllGroupsJavascript(JavascriptWidget):
    """Replace the fieldset legend with a select all checkbox."""

    body = open(
        os.path.join(os.path.dirname(__file__), "select.js"),
        'rb').read()


class ListSubscribeForm(SubscribeForm):
    description = _(u"Select subscription options and submit form.")

    # Add Javascript widget
    fields = field.Fields(SelectAllGroupsJavascript(schema.Field(
        __name__="js", required=False), mode="hidden"))

    # Include form fields, but change the order around.
    fields += SubscribeForm.fields.select('interests', 'name', 'email')

    # Add mailinglist as hidden field
    fields += field.Fields(schema.ASCII(
        __name__="list_id",
        required=True,
        ), mode="hidden")

    # Remove prefix; we want to be able to provide defaults using a
    # simple format.
    prefix = ""

    @property
    def label(self):
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
        return self.context.portal_url()

    def updateWidgets(self):
        # XXX: We override this to be able to set the prefix.
        self.widgets = getMultiAdapter(
            (self, self.request, self.getContent()), IWidgets)
        self.widgets.mode = self.mode
        self.widgets.prefix = ""
        self.widgets.ignoreContext = self.ignoreContext
        self.widgets.ignoreRequest = self.ignoreRequest
        self.widgets.ignoreReadonly = self.ignoreReadonly
        self.widgets.update()


ListSubscribeForm = wrap_form(ListSubscribeForm)


class ListSubscribeFormFieldWidgets(field.FieldWidgets):
    prefix = ""
