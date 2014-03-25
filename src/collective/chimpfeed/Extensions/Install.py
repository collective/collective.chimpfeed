from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import log
from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError
import transaction

from collective.chimpfeed.interfaces import IApiUtility

def install(self):
    setup_tool = getToolByName(self, 'portal_setup')
    setup_tool.runAllImportStepsFromProfile('profile-collective.chimpfeed:default')
    return "Imported install profile."


def uninstall(self, reinstall=False):
    if reinstall:
        return "Uninstall profile skipped"
    setup_tool = getToolByName(self, 'portal_setup')
    # setup_tool.runAllImportStepsFromProfile('profile-collective.chimpfeed:uninstall',
    #                                         ignore_dependencies=True)

    # Remove utilities when really uninstalled
    sm = self.getSiteManager()
    try:
        my_utility = getUtility(IApiUtility)
        sm.unregisterUtility(my_utility, IApiUtility)
        del my_utility
    except ComponentLookupError:
        pass

    adapters = sm.utilities._adapters
    for x in adapters[0].keys():
        if x.__module__.find("collective.chimpfeed") != -1:
            print "deleting %s" % x
            del adapters[0][x]
    sm.utilities._adapters = adapters

    subscribers = sm.utilities._subscribers
    for x in subscribers[0].keys():
        if x.__module__.find("collective.chimpfeed") != -1:
            print "deleting %s" % x
            del subscribers[0][x]
    sm.utilities._subscribers = subscribers

    provided = sm.utilities._provided
    for x in provided.keys():
        if x.__module__.find("collective.chimpfeed") != -1:
            print "deleting %s" % x
            del provided[x]
    sm.utilities._provided = provided

    transaction.commit()
    self.getPhysicalRoot()._p_jar.sync()
    log("Uninstalled collective.chimpfeed IApiUtility")

    return "Ran all uninstall steps."