Changes
=======

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
