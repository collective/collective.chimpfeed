from z3c.form import form
from z3c.form import button

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage

from zope.annotation.interfaces import IAnnotations
from zope.interface import classImplements
from plone.z3cform import layout

from collective.chimpfeed import MessageFactory as _

ANNOTATION_KEY = 'collective.chimpfeed'


def annotation_proxy(context, schema):
    annotations = IAnnotations(context)
    properties = dict(
        (name, AnnotationProperty(annotations, schema[name]))
        for name in schema
        )

    properties['portal_url'] = staticmethod(context.portal_url)

    proxy = type(
        "%sAdapter" % schema.__name__[1:],
        (object, ), properties,
        )

    classImplements(proxy, schema)

    return proxy()


class AnnotationProperty(object):
    def __init__(self, annotations, field):
        self.annotations = annotations
        self.field = field

    def __get__(self, inst, owner):
        annotation = self.annotations.get(ANNOTATION_KEY, {})
        return annotation.get(self.field.__name__, self.field.default)

    def __set__(self, inst, value):
        annotation = self.annotations.get(ANNOTATION_KEY, {})
        annotation[self.field.__name__] = value
        self.annotations[ANNOTATION_KEY] = annotation


class RegistryEditForm(form.EditForm):
    control_panel_view = "plone_control_panel"

    def getContent(self):
        return annotation_proxy(self.context, self.schema)

    @button.buttonAndHandler(_(u"Save"), name='save')
    def handleSave(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        self.applyChanges(data)
        IStatusMessage(self.request).addStatusMessage(
            _(u"Changes saved."), "info"
            )

        self._redirect()

    @button.buttonAndHandler(_(u"Cancel"), name='cancel')
    def handleCancel(self, action):
        IStatusMessage(self.request).addStatusMessage(
            _(u"Edit cancelled."), "info"
            )

        self._redirect()

    def _redirect(self):
        self.request.response.redirect(
            "%s/%s" % (self.context.absolute_url(),
                       self.control_panel_view)
            )


class ControlPanelFormWrapper(layout.FormWrapper):
    index = ViewPageTemplateFile('controlpanel.pt')
