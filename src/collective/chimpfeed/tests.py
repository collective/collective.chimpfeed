import sys

from Products.Five.testbrowser import Browser
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup
from Products.Five import zcml
from Products.Five import fiveconfigure
from Testing import ZopeTestCase as ztc

packages = (
    'collective.chimpfeed',
    )


@onsetup
def setup_product():
    fiveconfigure.debug_mode = True

    for package in packages:
        __import__(package)
        module = sys.modules[package]

    zcml.load_config('configure.zcml', module)

    fiveconfigure.debug_mode = False

    for package in packages:
        ztc.installPackage(package)

setup_product()
ptc.setupPloneSite(products=packages)


class BaseFunctionalTestCase(ptc.FunctionalTestCase):
    def afterSetUp(self):
        ptc.FunctionalTestCase.afterSetUp(self)

        self.browser = Browser()
        self.browser.handleErrors = False
        self.portal.error_log._ignored_exceptions = ()

        def raising(self, info):
            import traceback
            traceback.print_tb(info[2])
            print info[1]

        from Products.SiteErrorLog.SiteErrorLog import SiteErrorLog
        SiteErrorLog.raising = raising

    def loginAsAdmin(self):
        from Products.PloneTestCase.setup import portal_owner, default_password
        browser = self.browser
        browser.open(self.portal_url + "/login_form")
        browser.getControl(name='__ac_name').value = portal_owner
        browser.getControl(name='__ac_password').value = default_password
        browser.getControl(name='submit').click()

    @property
    def portal_url(self):
        return self.portal.absolute_url()


class PortletTest(BaseFunctionalTestCase):
    def clickAddPortlet(self):
        browser = self.browser
        browser.open(self.portal_url)
        browser.getLink('Manage portlets').click()
        right_column = browser.getForm(index=3)
        right_column.getControl('Subscription portlet').selected = True
        right_column.submit()

    def test_add_portlet(self):
        self.loginAsAdmin()
        self.clickAddPortlet()
        self.browser.getControl('Save').click()
