from Products.CMFCore.permissions import setDefaultRoles

MODERATE_PERMISSION = "collective.chimpfeed: Moderate"
CAMPAIGN_PERMISSION = "collective.chimpfeed: Send or schedule campaign"

setDefaultRoles(MODERATE_PERMISSION, ('Manager', ))
setDefaultRoles(CAMPAIGN_PERMISSION, ('Manager', ))
