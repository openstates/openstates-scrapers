$(document).ready( function() {

    // make select2 work
    $("#id_abbr").select2({placeholder: "Select a State"}).change(
        function() { this.form.submit(); });
    // made form submit on change, hide submit button
    $('#state_select_submit').hide();
    $('#mainFilter .select2-container').css('width', '200px');

    // hot keys
    var doc = $(document);
    doc.bind("keydown", "alt+b", function(){window.location = '/{{abbr}}/bills/'});
    doc.bind("keydown", "alt+l", function(){window.location = '/{{abbr}}/legislators/'});
    doc.bind("keydown", "alt+c", function(){window.location = '/{{abbr}}/committees/'});
    doc.bind("keydown", "esc", function(){$('#id_q').focus()});

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

    // Favorite buttons.
    $(".favorite-button").click(function(event){
        var favorite_div = $(this).parent(),
            favorite_msg = $(favorite_div).find('.favorite-message');

        $.ajax({
          type: 'POST',
          url: '/user/set_favorite',
          data: favorite_div.data(),
          dataType: 'json',
          headers: {'X-CSRFToken': getCookie('csrftoken')},
          success: function(){
            console.log("Favorite button got clicked.");
            console.log(favorite_div.data());
            if (favorite_div.data('is_favorite')) {
                favorite_msg.text("Follow again");
            } else {
                favorite_msg.text("Unfollow");
                }
            // Toggle is_favorite.
            favorite_div.data('is_favorite', !favorite_div.data('is_favorite'));
            },
          error: function(){
            favorite_msg.text("Ack! Something went wrong.");
        }
        });
        event.preventDefault();
    });

});

var clickable_rows = function(selector) {
    // Make table rows clickable.
    var trs = $(selector);
    var trs_count = trs.length;
    trs.click(function(){
        var location = $(this).find("a").attr("href");
        if (location) {
            window.location = location;
            return false;
        }
    });

    // If javascript is enabled, change cursor to pointer over table rows
    // and add selected class on hover.
    trs.css('cursor', 'pointer');
    trs.hover(function(){
            $(this).addClass('selected');
        },
        function(){
            $(this).removeClass('selected');
        }
    );
};

var fix_images = function() {
    // this URL will change
    var placeholder = 'http://static.openstates.org/assets/v2/images/placeholder.png';
    $('img.legImgSmall').error(function() {
            $(this).attr("src", placeholder).attr(
                "title", "No Photo Available");
    });
};

var pjax_setup = function(){

    $('form#toggleBtns button').click(function(e){

        // Prevent the normal form submission.
        e.preventDefault();

        // Derive the form url.
        var form_url = $('form#toggleBtns').attr('action');
        var value = $(this).attr('value');
        form_url = form_url + '?chamber=' + encodeURIComponent(value);

        // Use pjax to retrieve and insert the new content.
        $.pjax({
              url: form_url,
              container: 'div[data-pjax]'
        });
    });
};

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


// Favorites notificactions.
function setup_notification_radios() {
    $('.notification-preference input[type="radio"]').change(function(){
        var input = $(this),
            on_off = input.attr('value'),
            obj_type = input.closest('.notification-preference').data('obj_type');

        $.ajax({
              type: 'POST',
              url: '/user/set_notification_preference',
              data: {'obj_type': obj_type, 'on_off': on_off},
              dataType: 'json',
              headers: {'X-CSRFToken': getCookie('csrftoken')},
              success: function(){
                var msg = $(".notification-preference .message-" + obj_type);
                console.log(obj_type + ' notifications ' + on_off);
                msg.text(obj_type + ' notifications ' + on_off + '.');
                },
              error: function(){
                var msg = $("notification-preference message-" + obj_type);
                msg.text("Ack! Something went wrong.");
            }
            });
    });
}


// Find your legislator.
// "<p class = 'find_your_legislator_infobox' >" +
//                 "Or let us find your legislators based on your " +
//                 "<a id = 'do_geo_locate' href = '#' >" +
//                 "current location</a>." +
//                 "</p>"
function setup_find_your_legislator(success_append_html) {
    var map,
        needs_update = true;
        overlays   = [],
        chambers = { /* These colors will be used to fill and outline the
                        gmap for the districts. */
            "lower": {
                "stroke": "#484a02",
                "fill": "#eff508"
            },
            "upper": {
                "stroke": "#1b261a",
                "fill": "#94d28c"
            },
            "joint": {
                "stroke": "#072026",
                "fill": "#24aed1"
            }
        };
    map = new GMaps({
        div: '#map',
        lat: 38,
        lng: -97,
        zoom: 3
    });

    window.map = map;

    function do_geo_locate(lat, lon) {
        /* This is invoked when we want to re-draw the map. We get here either
           from the "submit" button, or clicking on the href with an overloaded
           click event. */
        var url = '/find_your_legislator/?lat=' +
               lat +
               '&lon=' +
               lon;
        /* This is a big operation. Kicking it off, since it's async */
        $.getJSON(url + "&boundary=y", function(data) {
            for ( var i in overlays ) {
                map.removeOverlay(overlays[i]);
            }
            overlays = [];
            for ( var i in data ) {
                var bdry = data[i],
                    polygon;
                for ( var n in bdry.shape ) {
                    for ( var j in bdry.shape[n] ) {
                        var bak_shape = bdry.shape[n][j],
                            shape = [],
                            lay = chambers[bdry['chamber']];
                        for ( var node in bak_shape ) {
                            node = bak_shape[node];
                            shape.push([node[1], node[0]]);
                        }
                        polygon = map.drawPolygon({
                            paths:         shape,
                            strokeColor:   lay['stroke'],
                            strokeOpacity: 1,
                            strokeWeight:  3,
                            fillColor:     lay['fill'],
                            fillOpacity:   0.3
                            });
                        overlays.push(polygon);
                    }
                }
            }
            // map.removeMarkers();
            needs_update = false;
        });

        /* Before we dispatch our request, we've already
           geo-located. Let's center first. */
        map.setZoom(12);
        map.setCenter(
            lat,
            lon
        );

        $("#results_table").html("<center>Loading....</center>");
        $("#results_table").load(url, function() {
            for ( var i in chambers ) {
                /* Colorize the results on the district table - it helps
                   make who is which district more clear. We need a solution
                   for more then one legislator for a chamber */
                var chamber = chambers[i];
                $(".chamber-" + i).css("background-color", chamber.fill);
                }
            // fix images after ajax load
            fix_images();
        });
    }
    $('#find_your_leg').submit(function(e){
        e.preventDefault();
        GMaps.geocode({
            address: $('#leg_search').val().trim(),
            callback: function(results, status){
                if ( status == 'OK' ){
                    /* We've got a lat/lon, let's call the render */
                    var  latlng = results[0].geometry.location,
                            lat = latlng.lat(),
                            lon = latlng.lng();
                    do_geo_locate(lat, lon);
                }
            }
        });
    });
    GMaps.geolocate({
        success: function(position) {
            $("#communicate").append(success_append_html);
            $("#do_geo_locate").click(function() {
                do_geo_locate(position.coords.latitude,
                    position.coords.longitude);
                return false;
            });
        },
        error: function(error) {
            /* $("#communicate").append("<p class = 'find_your_legislator_errorbox' >" +
            "We were not able to guess your location. Please enter in your details."+
            "</p>"); */
        }
    });
    if ( $("#_request").val().trim() !== "" ) {
        /* Auto-submit if we've got something in there (?q= param) */
        $('#find_your_leg').submit();
    }
}

function toTitleCase(str)
{
    return str.replace(/\w\S*/g, function(txt){
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
}


// Profile form.
function user_profile_form_submit(){
    var center, lat, lng, lat_input, lng_input, form_data, location_text,
        profile_form = $("#profile_form");

    center = map.getCenter();
    lat = center.lat();
    lng = center.lng();
    location_text = $("#leg_search").val();

    location_text_input = $('<input type="hidden" name="location_text" value="' + location_text + '"></input>');
    lat_input = $('<input type="hidden" name="lat" value="' + lat + '"></input>');
    lng_input = $('<input type="hidden" name="lng" value="' + lng + '"></input>');
    profile_form.append(location_text_input);
    profile_form.append(lat_input);
    profile_form.append(lng_input);
}