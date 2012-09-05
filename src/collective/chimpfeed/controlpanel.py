import logging

from Products.CMFCore.utils import getToolByName

from Acquisition import ImplicitAcquisitionWrapper

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import implements
from zope.component import adapts
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from plone.z3cform import layout

try:
    from plone.app.registry.browser import controlpanel
    switch_on = None
except ImportError:
    from collective.chimpfeed import legacy as controlpanel
    from plone.z3cform.z2 import switch_on

from collective.chimpfeed.interfaces import IFeedSettings
from collective.chimpfeed.interfaces import IControlPanel
from collective.chimpfeed import MessageFactory as _
from collective.chimpfeed.feeds import make_urls
from collective.chimpfeed.vocabularies import feeds_factory
from collective.chimpfeed.vocabularies import lists_factory

from z3c.form import field
from z3c.form import widget
from z3c.form.interfaces import IDataConverter

try:
    from z3c.form.browser import textlines
except ImportError:
    logging.warn("z3c.form library does not have textlines widget.")
    textlines = None

logger = logging.getLogger("collective.chimpfeed.controlpanel")


class ControlPanelAdapter(object):
    adapts(IFeedSettings)
    implements(IControlPanel)

    def __init__(self, settings):
        self.settings = settings

    @property
    def urls(self):
        portal_url = getToolByName(self.settings, 'portal_url')()

        vocabulary = feeds_factory(self.settings)

        # Use term's titles as the basis for the feed URLs.
        urls = make_urls(vocabulary)

        return tuple(
            ("%s/++chimpfeeds++/%s" % (portal_url, url), title)
            for url, value, title in urls
            )

    @property
    def lists(self):
        portal_url = getToolByName(self.settings, 'portal_url')()
        vocabulary = lists_factory(self.settings)

        return tuple(
            ("%s/@@chimpfeed-subscribe?list_id=%s" % (
                portal_url, term.value), term.title)
            for term in sorted(vocabulary, key=lambda term: term.title)
            )



class UrlsWidget(widget.Widget):
    implements(IDataConverter)

    render = ViewPageTemplateFile("urls.pt")

    @classmethod
    def factory(cls, field, request):
        return widget.FieldWidget(field, cls(request))

    def toWidgetValue(self, value):
        return value


class ControlPanelEditForm(controlpanel.RegistryEditForm):
    schema = IFeedSettings
    fields = field.Fields(IControlPanel)

    label = _(u"MailChimp settings")
    description = _(
        u"Please configure an API-key and define one or more "
        u"feeds."
        )

    fields['urls'].mode = "display"
    fields['urls'].widgetFactory = UrlsWidget.factory

    fields['lists'].mode = "display"
    fields['lists'].widgetFactory = UrlsWidget.factory

    if textlines is not None:
        fields['feeds'].widgetFactory = textlines.TextLinesFieldWidget

    def updateActions(self):
        # This prevents a redirect to the main control panel page
        self.request.response.setStatus(200, lock=True)

        super(ControlPanelEditForm, self).updateActions()

    def render(self):
        if switch_on is not None:
            switch_on(self)

        urls = self.widgets['urls']
        urls.update()

        if not urls.value:
            del self.widgets['urls']

        return super(ControlPanelEditForm, self).render()

    def getContent(self):
        content = super(ControlPanelEditForm, self).getContent()
        return ImplicitAcquisitionWrapper(content, self.context)


ControlPanel = layout.wrap_form(
    ControlPanelEditForm,
    controlpanel.ControlPanelFormWrapper
    )
