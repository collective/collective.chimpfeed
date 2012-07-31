Overview
========

This package makes it easy to create newsletter content feeds or
campaigns from Plone based on content interest group tagging.

Simply define interest groups in your `MailChimp
<http://www.mailchimp.com>`_ list, configure Plone with your API key
and start tagging content.

The package also includes a subscription portlet that presents a
selection of interest groups, as well as a moderation portlet and a
portlet that lets an editor create, send or schedule a new campaign.


Compatibility
-------------

- Plone 3 and 4 (all versions);
- Archetypes or Dexterity.


Getting started
---------------

1. First, install the product using Plone's add-on control panel.

   This register a control panel, and adds a number of required
   indexes and columns to the catalog.

2. Visit the "MailChimp RSS" control panel to configure API key.

3. Tag content with interest groups.

Optionally,

5. Add one or more subscription portlets.


Feed content
------------

In the out of the box configuration, only the default dublin core
metadata will be returned in RSS feeds.

If a view ``rss-summary`` is registered for the item, the template
will call this view and include it as the RSS summary field (marked as
CDATA). The string should be HTML.


Localization
------------

The product is currently localized into:

* Danish

Contributions are welcome!


Author
------

Malthe Borch <mborch@gmail.com>
