from zope.formlib import form
from zope.interface import implements
from zope.interface import alsoProvides
from zope.interface import noLongerProvides
from plone.z3cform.interfaces import IWrappedForm
from plone.app.z3cform.interfaces import IPloneFormLayer
from z3c.form.interfaces import IFormLayer
from plone.app.portlets.portlets import base
from five.formlib.formbase import FormBase
from zope.security import checkPermission

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.chimpfeed.form import SubscribeForm
from collective.chimpfeed.form import ModerationForm
from collective.chimpfeed.interfaces import ISubscriptionPortlet
from collective.chimpfeed.interfaces import IModerationPortlet
from collective.chimpfeed import MessageFactory as _


class ModerationPortletAssignment(base.Assignment):
    implements(IModerationPortlet)

    heading = _(u"Moderation")

    title = _(u"Feed moderation")


class SubscriptionPortletAssignment(base.Assignment):
    implements(ISubscriptionPortlet)

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            self.__dict__[name] = value

    @property
    def title(self):
        return _("Subscribe: ${title}", mapping={'title': self.heading})


class FormPortletRenderer(base.Renderer):
    render = ViewPageTemplateFile('portlet.pt')

    def render_form(self):
        provided = IPloneFormLayer.providedBy(self.request)
        noLongerProvides(self.request, IPloneFormLayer)
        alsoProvides(self.request, IFormLayer)
        try:
            form = self.create_form()
            alsoProvides(form, IWrappedForm)
            form.update()
            return form.render()
        finally:
            noLongerProvides(self.request, IFormLayer)
            if provided:
                alsoProvides(self.request, IPloneFormLayer)


class ModerationPortletRenderer(FormPortletRenderer):
    @property
    def available(self):
        return checkPermission("chimpfeed.Moderate", self.context)

    def create_form(self):
        context = self.data.__of__(self.context)
        return ModerationForm(context, self.request)


class SubscriptionPortletRenderer(FormPortletRenderer):
    def create_form(self):
        context = self.data.__of__(self.context)
        return SubscribeForm(context, self.request)


class ModerationPortletAddForm(base.NullAddForm):
    def create(self):
        return ModerationPortletAssignment()


class SubscriptionPortletForm(FormBase):
    form_fields = form.Fields(ISubscriptionPortlet)
    description = _(u"This portlet shows a subscription form.")

    def setUpWidgets(self, **kwargs):
        super(SubscriptionPortletForm, self).setUpWidgets(**kwargs)

        widget = self.widgets['mailinglist']
        if len(widget.vocabulary):

            mailinglist = ISubscriptionPortlet.providedBy(self.context) and \
                          self.context.mailinglist or widget.hasInput() \
                          and widget.getInputValue()

            if mailinglist:
                pass
            else:
                # Make a default choice
                token = tuple(widget.vocabulary)[-1].token
                widget.setRenderedValue(token)
        else:
            self.widgets['interest_groups'].hidden = True
            self.widgets['interest_groupings'].hidden = True


class SubscriptionPortletAddForm(SubscriptionPortletForm, base.AddForm):
    label = _(u"Add Subscription Portlet")

    def create(self, data):
        return SubscriptionPortletAssignment(**data)


class SubscriptionPortletEditForm(SubscriptionPortletForm, base.EditForm):
    label = _(u"Edit Subscription Portlet")
