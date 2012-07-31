from zope.formlib import form
from zope.interface import implements
from zope.interface import alsoProvides
from zope.interface import noLongerProvides

try:
    from plone.z3cform.interfaces import IWrappedForm
except ImportError:
    IWrappedForm = None
    from plone.z3cform.z2 import switch_on

try:
    from plone.app.z3cform.interfaces import IPloneFormLayer
except:
    from Products.CMFDefault.interfaces import ICMFDefaultSkin as \
         IPloneFormLayer

from z3c.form.interfaces import IFormLayer
from plone.app.portlets.portlets import base

try:
    from five.formlib.formbase import FormBase
except ImportError:
    from Products.Five.formlib.formbase import FormBase

from zope.security import checkPermission

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFDefault.interfaces import ICMFDefaultSkin

from collective.chimpfeed.form import CampaignForm
from collective.chimpfeed.form import SubscribeForm
from collective.chimpfeed.form import ModerationForm
from collective.chimpfeed.interfaces import ISubscriptionPortlet
from collective.chimpfeed.interfaces import IModerationPortlet
from collective.chimpfeed.interfaces import ICampaignPortlet
from collective.chimpfeed import MessageFactory as _


class CampaignPortletAssignment(base.Assignment):
    implements(ICampaignPortlet)

    heading = _(u"Campaign scheduling")
    description = _(u"Send or schedule a newsletter campaign.")

    title = _(u"Campaign portlet")

    start = None
    section = u"std_content00"

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            self.__dict__[name] = value


class ModerationPortletAssignment(base.Assignment):
    implements(IModerationPortlet)

    heading = _(u"Feed moderation")
    description = _(u"Use this form to moderate content.")

    title = _(u"Moderation portlet")


class SubscriptionPortletAssignment(base.Assignment):
    implements(ISubscriptionPortlet)

    description = None

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            self.__dict__[name] = value

    @property
    def title(self):
        return _("Subscribe: ${title}", mapping={'title': self.heading})


class FormPortletRenderer(base.Renderer):
    render = ViewPageTemplateFile('portlet.pt')

    name = ""

    def render_form(self):
        provided = IPloneFormLayer.providedBy(self.request)
        noLongerProvides(self.request, IPloneFormLayer)
        alsoProvides(self.request, IFormLayer)
        try:
            form = self.create_form()
            if IWrappedForm is None:
                switch_on(self)
                alsoProvides(self.request, ICMFDefaultSkin)
            else:
                alsoProvides(form, IWrappedForm)
            form.update()
            return form.render()
        finally:
            noLongerProvides(self.request, IFormLayer)
            if provided:
                alsoProvides(self.request, IPloneFormLayer)


class ModerationPortletRenderer(FormPortletRenderer):
    name = "Moderation"

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


class CampaignPortletRenderer(FormPortletRenderer):
    def create_form(self):
        context = self.data.__of__(self.context)
        return CampaignForm(context, self.request)


class CampaignPortletAddForm(base.AddForm):
    label = _(u"Add campaign portlet")
    form_fields = form.Fields(ICampaignPortlet)

    # Let's not ask the user to name a start date on adding the
    # portlet.
    form_fields = form_fields.omit('start')

    def create(self, data):
        return CampaignPortletAssignment(**data)


class CampaignPortletEditForm(base.EditForm):
    label = _(u"Edit campaign portlet")
    form_fields = form.Fields(ICampaignPortlet)


class ModerationPortletAddForm(base.NullAddForm):
    def create(self):
        return ModerationPortletAssignment()


class SubscriptionPortletForm(FormBase):
    name = "Subscribe"

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
