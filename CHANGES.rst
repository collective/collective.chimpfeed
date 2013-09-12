Changes
=======

1.9.9 (2013-09-12)
------------------

Changes:

- Renamed feed.pt to feed.pt.xml to ensure i18ndude works for translations, and 
  correct a pep8 related issue.
  [bosim] 

- Updated translations in general including danish translations.
  [bosim]

- Translations for portlet titles and descriptions are now in the plone domain.
  [bosim]

- Some Plone 4.3+ changes.
  [senner]


1.9.8 (2012-01-25)
------------------

Bugfixes:

- Use date and time as upper limit in campaign portlet to include
  todays content.
  [tmog]

- Don't fail when no name is entered
  [tmog]

- Moved catalog indexes to setuphandlers to avoid indexes being
  emptied when profile is run.
  [tmog]

- Fixed broken subscribe form. Bug introduced with pre-selected
  interest groups feature on subscribe portlet.

- Fixed interest groups selection (on assignment) being ignored when
  ``select_interest_groups`` was False.

- Add dependency on BeautifulSoup. It's required for the default
  static newsletter renderer.

- Update title and description of newsletter portlet.
  So we can tell the difference between newsletter and campaign.

Changes:

- Use context description on main subscribe form if there is
  one and the form is rendered in a custom context.
  Added for flexibility.
  [tmog]

- Main subscribe form no longer registered on plone site.
  Means flexibility to view the form in a custom context.
  Tip: use a Link as default_page in you context.
  [tmog]

- Added control panel option to enable select all javascript
  on subscribe form. Upgradestep to update registry included.
  [tmog]

- Added hook to register named IGroupExtras utilities. Can be used
  in custom code to inject results into a feed.
  [tmog]

- Ensure campaign template does not fail if items have no getObject.
  This adds flexibility when customising.
  [tmog]

- Added control panel option to ignore interest groupings.
  Ignored groupings will be filtered from the feed vocabulary.
  [tmog]


1.9.7 (2012-12-07)
------------------

- Sort items for RSS-feed by publication date.


1.9.6 (2012-12-05)
------------------

Bugfixes:

- Fixed compatibility with Python 2.4.

- The RSS-feed now defines only ``pubDate` for each entry and not also
  ``dc:date``. According to the w3 validation service, "An item should
  not include both pubDate and dc:date".

Changes:

- When creating new campaigns, we now specify a segment that filters
  away any subscribers who are not interested in anything we're sending.
  [tmog]


1.9.5 (2012-11-16)
------------------

Bugfixes:

- Correctly hide form fields that have the 'show' attribute set to
  false.


1.9.4 (2012-11-16)
------------------

Bugfixes:

- The campaign preview view is adapted to the parent context.


1.9.3 (2012-11-16)
------------------

Bugfixes:

- Use Five-based template class such that e.g. `z3c.jbot
  <http://pypi.python.org/pypi/z3c.jbot>`_ can override the template.

Changes:

- The feed schedule field is now set up with its own write permission.

- The subscription form handler now redirects to itself, with all
  widgets removed (but displaying a status message).

- The campaign preview view is now adapted to the current context
  instead of the site.

1.9.2 (2012-11-12)
------------------

Bugfixes:

- Fixed issue where interest group filtering would incorrectly get
  applied on the outer level which would then be repeated
  unnecessarily.

1.9.1 (2012-11-09)
------------------

Bugfixes:

- Fixed encoding issue.

1.9.0 (2012-11-09)
------------------

- Hidden field corresponds to 'public', 'show' is something else.

1.8.9 (2012-11-09)
------------------

Bugfixes:

- Use the interest grouping title intead of the group title in the
  campaign template.

Features:

- The default subject line now includes the date.

- Attempt to translate field names.

1.8.8 (2012-11-06)
------------------

Bugfixes:

- Fixed issue where the moderation portlet would incorrectly return
  items that would not need moderation.

Features:

- Added control panel action to remove non-existing feeds from content.

1.8.7 (2012-11-05)
------------------

Bugfixes:

- "System" fields (those in all-caps) are now no longer shown on the
  subscription form.

Features:

- Require that 'Anonymous' is included in allowed roles and groups.

- The subscription form now includes a "Select all" checkbox.

1.8.6 (2012-10-30)
------------------

Bugfixes:

- Update moderation items widget when one or more items have been
  approved. This ensures that the rendered view is correctly updated.

1.8.5 (2012-10-30)
------------------

Bugfixes:

- Fixed encoding issue that affected the rendering of a status message
  for 'bumped items'.

1.8.4 (2012-10-30)
------------------

Bugfixes:

- An item which has no scheduled date, but is approved, now correctly
  gets today's date assigned. This fixes an issue where the item would
  not appear in the moderation form after approval. With this change,
  it will appear at least on the day of approval.

1.8.3 (2012-10-29)
------------------

Features:

- Use Plone's standard identifier normalization to convert interest
  groups into form tokens on the automatically generated subscription
  form.

Bugfixes:

- Fixed issue with acquisition-wrapping such that subscription form
  defaults actually work.

- Subscription form would incorrectly load interest groupings for all
  available lists.

Logging:

- Log every API call to MailChimp.

- If a campaign can't be created, show the error message in the status
  message, not just the log.

1.8.2 (2012-10-29)
------------------

Features:

- The subscription form now displays defined 'text' and 'dropdown'
  merge vars as fields.

Bugfixes:

- The previous release had a bugfix which did not address the issue
  correctly. This should be fixed now.

- Made the schema extension adapter browser-layer aware, to avoid
  extending schemas on sites where the package is not installed
  (editing objects would fail if chimpfeed was not installed).
  [sunew]

- Fixed an issue setting up chimpfeed on a vanilla plone site, where
  the feeds setting is initialized to None.
  [sunew]

1.8.1 (2012-10-12)
----------------

Bugfixes:

- Fixed an issue where the moderation portlet would fail when an item
  set for moderation would not have a defined schedule date.

  This shouldn't happen in practice, because the publication date is
  used instead of a schedule date, but the catalog data might be
  incorrect.

1.8 (2012-09-12)
----------------

Features:

- The list subscribe form now validates the e-mail address input.

- You can define feeds manually in addition to the ones pulled
  automatically from a selected list. This is now also clarified in
  the help texts.

- Added local utility IApiUtility (defined in interfaces) to expose methods
  for accessing the API, to be used my third party customizations.

- Show unmoderated items even if they're scheduled for a past date.

- Added an option to exclude items scheduled after today's date when
  preparing a campaign.

- Adding RSS publication date, formatted as RFC 822.

Bugfixes:

- Fixed an issue where the javascript template would break on
  rendering.

- Fixed an issue where KSS validation would not work properly in the
  subscribe form.

- Fixed an off-by-one bug in the date comparison logic. Items are now
  correctly included from the provided "start" date.

- feedSchedule is now defined as a DateIndex.

1.7 (2012-08-02)
----------------

Features:

- It's now possible to restrict the collection of interest groups to
  those from a particular list. This can help clear up confusion about
  which interest groups are available, but importantly, also helps
  alleviate network latency when many lists are defined for an account
  (because we must query the interest groups per list, in sequence).

- Added a subscription form, available from the control panel (there's
  a link for each defined mailinglist).

  The subscription form includes a javascript-snippet that lets a
  visitor select all interest groups within a particular grouping
  using a "select all" (or subsequently none) checkbox.

1.6 (2012-07-31)
----------------

Changes:

- Interest groups are now conflated with feeds. These are now always
  defined in MailChimp.

  Previously, a manager needed to set up a list of feeds
  manually. These were just strings that did not tie into MailChimp's
  interest groups directly. This is now changed.

Bugfixes:

- Feed URLs in the control panel are now listed in the same order as
  they are defined.

Features:

- Added new schema extension to give items an explicit feed category.

  Available categories are configured in the control panel.

- It's now possible to create and schedule a a new campaign based on
  the items currently active.

  This is implemented as a new portlet. It is intended that the
  portlet be added to the editor's dashboard.

  Note that content is grouped by their interest group marking, and
  uses MailChimp's conditional markup to tailor the newsletter to each
  user. The sorting of the groups is pluggable via a utility.

  The portlet includes a date which sets the lower date boundary on
  what items are active. The upper boundary defaults to today's date
  which is matched with the item schedule date.

  When a campaign is created, tomorrow's date is set as the new lower
  date boundary such that no items are immediately active for a
  subsequent campaign.

1.5.7 (2012-06-19)
------------------

Compatibility:

- Fixed compatibility issues with legacy libraries.

1.5.6 (2012-06-18)
------------------

Bugfixes:

- Provide title explicitly; the RSS template checks for this attribute
  using explicit acquisition.

1.5.5 (2012-06-08)
------------------

Features:

- Added optional portlet description field.

1.5.4 (2012-04-25)
------------------

- Fixed bug that would make the schema extension fail with
  Archetypes-based content.

1.5.3 (2012-04-19)
------------------

- Do not extend schema (or add via behavior) if product is not
  installed (settings not available).

1.5.2 (2012-04-19)
------------------

Features:

- Use "Publishing date" when feed schedule is unset.

Changes:

- The feed now only includes items in the 'published' workflow state.

Bugfixes:

- Fixed issue on Archetypes where the feed schedule date would default
  to today's date (instead of ``None``).

- Fixed issue where ``effective_date`` would return 0 due to explicit
  acquisition. The attribute is now declared as "acquired" which
  informs the explicit wrapper to yield the contained attribute.

- Fixed issue where an RSS-feed would fail for content which does not
  provide a ``getText`` method.

1.5.1 (2012-04-18)
------------------

Bugfixes:

- Fixed issue where the Archetypes schema extender would replace
  existing fields (if using the same names), for example
  ``"feeds"``.

  Instead, the extender now ignores such content types (a warning is
  logged).


1.5 (2012-04-11)
----------------

Features:

- Plone 3 compatibility.

Bugfixes:

- Fixed issue where subscription using first name only (single name,
  when split on space) would cause an exception.


1.4 (2012-03-27)
----------------

Features:

- Bump schedule date to today's date on moderation, if date is in the
  past. This ensures that the item will be shown on the moderation
  screen.

Bugfixes:

- Fixed issue with custom schema mutator which would not function
  correctly with schema caching; we are able to work around it using
  Archetypes' storage API directly.

- Fixed incorrect package dependency.


1.3 (2012-03-26)
----------------

Features:

- Add support for configuring an RSS summary display of included
  items.

- Add support for Dexterity-based content.

- Make content moderation requirement optional.


1.2 (2012-03-09)
----------------

Features:

- Add link to content for moderation.

Bugfixes:

- The moderation portlet now correctly gets the class
  ``'portletModeration'``.

1.1 (2012-03-08)
----------------

- Added simple approval system where items are explicitly made
  available after some date, and separately approved (guarded by a
  custom permission).

  To upgrade, you must run the "catalog" setup step and perform the
  require indexing.

1.0 (2012-01-18)
----------------

- Initial public release.
