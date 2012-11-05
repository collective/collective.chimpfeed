jQuery(function($) {
  var groups = $("fieldset.interest-group");
  var select_all = $(
      '<fieldset class="interest-group">' +
      '  <div style="border: none; margin-bottom: 0; padding-bottom: 0">' +
      '    <input type="checkbox" class="checkbox-widget" ' +
      '           id="interest-group-select-all" />' +
      '    <label for="interest-group-select-all">' +
      '      <span class="label" style="font-weight: bold">Select all</span>' +
      '    </label>' +
      '  </div>' +
      '</fieldset>     ');
  groups.first().before(select_all);
  $.each(groups, function(i, j) {
    var checkboxes = $(j).find("input[type=checkbox]");
    checkboxes.next('label').find('span').css('font-weight', 'normal');
    var legend = $(j).find("legend");
    var title = legend.text();
    var id = 'interest-group-select-all-' + i;
    select = $(
        '<div>' +
        '<input id="' + id + '" ' +
        'type="checkbox" class="checkbox-widget" />' +
        '<label for="' + id + '">' +
        '<span class="label"> ' + title + ' </span>' +
        '</label>' +
        '</div>');
    legend.replaceWith(select);
    select.find("input").click(function() {
      var checked = $(this).attr("checked");
      checkboxes.attr("checked", checked);
    });
  });
  var checkboxes = $(groups).find("input[type=checkbox]");
  select_all.find("input").click(function() {
      var checked = $(this).attr("checked");
      checkboxes.attr("checked", checked);
    });
});
