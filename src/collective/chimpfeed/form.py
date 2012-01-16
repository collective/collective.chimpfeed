import time
import greatape

from Products.statusmessages.interfaces import IStatusMessage
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.registry.interfaces import IRegistry
from plone.memoize.ram import cache
from plone.memoize.instance import memoizedproperty

from zope.i18n import negotiate
from zope.component import getUtility
from zope.component import queryUtility
from zope.interface import Interface
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope import schema

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
        title=_(u"Interests"),
        value_type=schema.Choice(
            vocabulary="collective.chimpfeed.vocabularies.InterestGroups",
            ),
        required=False,
        )


class InterestsWidget(SequenceWidget):
    template = ViewPageTemplateFile("interests.pt")

    @cache(lambda *args: time.time() // (60 * 60))
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
            for name in groups.get(grouping_id):
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

            result = self.renderChoices(terms, grouping['name'])
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

        widget.update()

        if label is not None:
            widget.label = label

        return widget.render()


class SchemaErrorSnippet(object):
    implements(IErrorViewSnippet)

    def __init__(self, error, request, widget, field, form, content):
        self.error = error

    def update(self):
        pass

    def render(self):
        return _(self.error.__doc__)


class SubscribeForm(form.Form):
    fields = field.Fields(ISubscription)

    fields['interests'].widgetFactory = InterestsWidget.factory

    ignoreContext = True

    @property
    def action(self):
        return self.context.aq_parent.absolute_url()

    @button.buttonAndHandler(u'Register')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        settings = getUtility(IRegistry).forInterface(IFeedSettings)
        api_key = settings.mailchimp_api_key

        try:
            list_id = self.context.mailinglist

            email = data['email']
            name = data['name']
            interests = data['interests']

            if api_key:
                api = greatape.MailChimp(api_key, debug=True)

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
                    logger(exc)

                if result:
                    return IStatusMessage(self.request).addStatusMessage(
                        _(u"Thank you for signing up. We'll send you a "
                          u"confirmation message by e-mail shortly."), "info")

            IStatusMessage(self.request).addStatusMessage(
                _(u"An error occurred while processing your "
                  u"request to sign up for ${email}. "
                  u"Please try again!", mapping={'email': email}),
                "error")

        finally:
            self.request.response.redirect(self.action)
