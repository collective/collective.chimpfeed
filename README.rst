Overview
========

This package makes it easy to designate content into one or more named
feeds, suitable for creating automated newsletter content.

It extends the base content schema for any Archetypes-based content
which lets editors easily manage which feeds (if any) that a given
item should be listed under.

Designed for the `MailChimp <http://www.mailchimp.com>`_ internet
service, the package also includes a subscription portlet that
optionally lists a subset of interest groups.


Compatibility
-------------

Plone 3 and 4 (all versions).


Getting started
---------------

1. First, install the product using Plone's add-on control panel.

   This register a control panel, and adds a number of required
   indexes and columns to the catalog.

2. Visit the "MailChimp RSS" control panel to define one or more
   feeds.

3. Enable one or more feeds for your content by clicking "Edit" and
   selecting from the "Feeds" option.

Optionally,

4. Configure a MailChimp API-key (also available in the control panel).

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
