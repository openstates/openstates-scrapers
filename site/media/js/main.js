$(document).ready( function() {
    // add placeholders
    $("input, textarea").placehold();

    // make select2 work
    $("#id_abbr").select2({placeholder: "Select a State"}).change(
        function() { this.form.submit(); });
    // made form submit on change, hide submit button
    $('#state_select_submit').hide();
    $('#mainFilter .select2-container').css('width', '200px');

    // add gigya
    var ua = new gigya.socialize.UserAction();
    ua.setTitle($('title').text());
    var params = {
        containerID: 'shareBtns',
        iconsOnly: true,
        layout: 'horizontal',
        noButtonBorders: true,
        shareButtons: 'facebook,twitter',
        shortURLs: 'never',
        showCounts: 'none',
        userAction: ua
    };
    gigya.socialize.showShareBarUI(params);
});
