Changes
=======

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
