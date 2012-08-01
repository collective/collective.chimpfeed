jQuery(function($) {
  $.each($("fieldset.interest-group"), function(i, j) {
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
});
