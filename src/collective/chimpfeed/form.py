import time
import math
import greatape
import cgi

from Products.statusmessages.interfaces import IStatusMessage
from Products.CMFCore.utils import getToolByName

from ZODB.utils import u64
from DateTime import DateTime

from plone.memoize.ram import cache
from plone.memoize.instance import memoizedproperty
from plone.memoize.volatile import DontCache

from zope.i18n import negotiate
from zope.i18n import translate
from zope.component import queryUtility
from zope.interface import Interface
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope import schema
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.widget import SequenceWidget
from z3c.form.widget import FieldWidget
from z3c.form.interfaces import IErrorViewSnippet
from z3c.form.browser.checkbox import CheckBoxFieldWidget

from collective.chimpfeed import MessageFactory as _
from collective.chimpfeed import logger
from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed.interfaces import INameSplitter
from collective.chimpfeed.vocabularies import interest_groups_factory
from collective.chimpfeed.splitters import GenericNameSplitter


def create_groupings(groups):
    groupings = {}
    for grouping_id, name in groups:
        groupings.setdefault(grouping_id, []).append(name)
    return groupings


def cache_on_get_for_an_hour(method, self):
    if self.request['REQUEST_METHOD'] != 'GET':
        raise DontCache

    return time.time() // (60 * 60), self.id


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

            days = int(math.floor(date - today))
            if days != last:
                entries = []

                # To-Do: Use Plone's date formatters
                if days == -1:
                    name = _(u"Today")
                elif days < 7:
                    abbr = date.strftime("%a")
                    name = translate(
                        'weekday_%s' % abbr.lower(),
                        domain="plonelocales",
                        context=self.request
                        )
                else:
                    name = self._localize_time(date, False)

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

    @memoizedproperty
    def groupings(self):
        return tuple(interest_groups_factory.get_groupings())

    def renderInterestGroups(self):
        groups = create_groupings(self.context.interest_groups)

        terms = []
        for grouping in self.groupings:
            grouping_id = grouping['id']
            names = groups.get(grouping_id, ())
            for group in grouping['groups']:
                name = group['name']
                if name in names:
                    term = interest_groups_factory.get_term_for_group(
                        name, grouping_id
                        )
                    terms.append(term)

        return self.renderChoices(terms)

    def renderInterestGroupings(self):
        filtered = (
            grouping for grouping in self.groupings
            if grouping['id'] in self.context.interest_groupings
            )

        rendered = []

        for grouping in filtered:
            terms = tuple(interest_groups_factory.get_terms_for_grouping(
                grouping, count=False
                ))

            # Create label from the grouping name; we simply lowercase
            # it.
            label = _(u"Choose ${name}:", mapping={
                'name': cgi.escape(grouping['name'].lower())
                })

            result = self.renderChoices(terms, label)
            rendered.append(result)

        return u"\n".join(rendered)

    def renderChoices(self, terms, label=None):
        choice = schema.Choice(
            vocabulary=SimpleVocabulary(terms),
            )

        field = self.field.bind(self.context)
        field.value_type = choice

        widget = CheckBoxFieldWidget(field, self.request)
        widget.name = self.name
        widget.id = self.id

        widget.update()
        result = widget.render()

        if label is not None:
            result = u"<fieldset><legend>%s</legend>%s</fieldset>" % (
                translate(label, context=self.request), result
                )

        return result


class SchemaErrorSnippet(object):
    implements(IErrorViewSnippet)

    def __init__(self, error, request, widget, field, form, content):
        self.error = error

    def update(self):
        pass

    def render(self):
        return _(self.error.__doc__)


class BaseForm(form.Form):
    ignoreContext = True

    @property
    def action(self):
        # Use the parent object's URL instead of the current request
        # URL; this avoids adding a view name to the end of the path.
        return self.context.aq_parent.absolute_url()

    @property
    def prefix(self):
        # Make sure form prefix is unique
        return 'form-%d-%d.' % (
            u64(self.context._p_oid),
            int(self.context._p_mtime) % 10000
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

                obj.reindexObject(['feedModerate'])

    def update(self):
        super(ModerationForm, self).update()

        # No reason to show a button if no action is required (or
        # possible).
        if not self.widgets['items'].action_required:
            del self.actions['approve']


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

        try:
            list_id = self.context.mailinglist

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
            self.request.response.redirect(self.action)
