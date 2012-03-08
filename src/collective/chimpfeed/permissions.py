from Products.CMFCore.permissions import setDefaultRoles

MODERATE_PERMISSION = "collective.chimpfeed: Moderate"

setDefaultRoles(MODERATE_PERMISSION, ('Manager', ))
