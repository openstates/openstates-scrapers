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

    // Favorite buttons.
    $(".favorite-button").click(function(event){
        var favorite_div = $(this).parent(),
            favorite_msg = $(favorite_div).find('.favorite-message'),
            favorite_btn = $(favorite_div).find('.favbutton'),
            favorite_star = $(favorite_div).find('.star');

        $.ajax({
          type: 'POST',
          url: '/favorites/set_favorite/',
          data: favorite_div.data(),
          dataType: 'json',
          headers: {'X-CSRFToken': getCookie('csrftoken')},
          success: function(){
            //console.log("Favorite button got clicked.");
            //console.log(favorite_div.data());
            if (favorite_div.data('is_favorite')) {
                favorite_star.removeClass('starOn');
                favorite_star.addClass('starOff');
                favorite_btn.text("Follow again");
            } else {
                favorite_star.removeClass('starOff');
                favorite_star.addClass('starOn');
                favorite_btn.text("Unfollow");
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
    var placeholder = 'http://static.openstates.org/assets/v3.1/images/placeholder.png';
    $('img.legImgSmall').error(function() {
            $(this).attr("src", placeholder).attr(
                "title", "No Photo Available");
    });
};

var img_error = function(img) {
    img.onerror = '';
    img.src = 'http://static.openstates.org/assets/v3.1/images/placeholder.png';
    return false;
}

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

var make_vote_charts = function(width, height, radius) {
    d3.selectAll('.vote-chart').each(function() {
        var data = [];
        d3.select(this).selectAll('table tbody tr').each(function() {
            var vote = {};
            vote.type = d3.select(this).select("td:first-child").text();
            // get text then remove ratio from table
            vote.count = d3.select(this).select("td:nth-child(3)").remove().text();
            data.push(vote);
        });
        var arc = d3.svg.arc().outerRadius(radius);
        var pie = d3.layout.pie().value(function(d) { return d.count; } );
        var vis = d3.select(this).insert('svg:svg', ':first-child')
            .data([data])
            .attr('width', width).attr('height', height)
            .attr('class', 'twoCol colLt')
            .append('svg:g')
            .attr('transform', 'translate(' + radius + ',' + radius + ')');
        var arcs = vis.selectAll('g.slice').data(pie).enter().append('svg:g').attr('class', 'slice');
        arcs.append('svg:path').attr('fill', function(d, i) {
            return ['#a3b56d', '#b85233', '#dfdfd2'][i];
        }).attr('d', arc);
    });
};

var round_up = function(n) {
    var denom = 1000;
    while(Math.ceil(n/denom) > 10) {
        denom *= 10;
    }
    return Math.ceil(n/denom)*denom;
}

var make_ie_chart = function() {
    d3.select('#ie-chart-container').each(function() {
        var data = [];
        var width = 460;
        var top_offset = 30;
        d3.select(this).selectAll('table tbody tr').each(function() {
            var d = {};
            d.year = d3.select(this).select("td:first-child").text();
            d.total = parseInt(d3.select(this).select("td:nth-child(2)").text().replace(/,/g, ''), 10);
            data.push(d);
        });
        var height = 20 * data.length;
        var chart = d3.select(this).append('svg')
            .attr('class', 'ie-chart')
            .attr('width', width)
            .attr('height', height + 2*top_offset);
        var max_x = round_up(d3.max(data, function(d) { return d.total; }));
        var x = d3.scale.linear().domain([0, max_x]).range([0, width-80]);
        var default_formatter = d3.format('n');
        var axis = d3.svg.axis().scale(x).ticks(4)
            .tickValues([0, max_x*0.25, max_x*0.5, max_x*0.75, max_x])
            .tickFormat(function(x) { return '$' + default_formatter(x); });
        chart.selectAll('rect').data(data)
            .enter().append('rect')
            .attr('x', 40)
            .attr('y', function(d, i) { return i * 20 + top_offset; })
            .attr('width', function(d) { return x(d.total); })
            .attr('height', 17)
            .attr('fill', '#a3b669');
        chart.selectAll('text').data(data).enter().append('text')
                .attr('x', 0)
                .attr('y', function(d, i) { return i * 20 + top_offset + 10; })
                .attr('dy', '.25em')
                .attr('fill', '#504a45')
                .text(function(d) { return d.year; });
        chart.append('text')
            .attr('x', 0)
            .attr('y', 0)
            .attr('dy', '1em')
            .attr('fill', '#504a45')
            .text('Campaign Contributions by Cycle')
        chart.append('svg:g')
            .attr('class', 'x-axis')
            .attr('transform', "translate(40," + (20*data.length+top_offset) + ')')
            .call(axis);
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

var sort_func_asc = function(a,b) {
    var DIGIT = /^\d+$/;
    if(DIGIT.test(a) && DIGIT.test(b)) {
        /* pure numbers */
        return parseInt(a, 10) - parseInt(b, 10);
    }

    /* if both have leading digits and they differ */
    var LDIGIT = /^\d+/;
    var da = LDIGIT.exec(a);
    var db = LDIGIT.exec(b);
    if((da && db) && (da[0] != db[0])) {
        return da[0] - db[0];
    }

    /* just compare as normal strings */
    return ((a < b) ? -1 : ((a > b) ?  1 : 0));
};

var sort_func_desc = function(a,b) { return sort_func_asc(b, a); };


// Favorites notificactions.
function setup_notification_radios() {
    $('.notification-preference input[type="radio"]').change(function(){
        var input = $(this),
            on_off = input.attr('value'),
            obj_type = input.closest('.notification-preference').data('obj_type');

        $.ajax({
              type: 'POST',
              url: '/favorites/set_notification_preference/',
              data: {'obj_type': obj_type, 'on_off': on_off},
              dataType: 'json',
              headers: {'X-CSRFToken': getCookie('csrftoken')},
              success: function(){
                var msg = $(".notification-preference .message-" + obj_type);
                //console.log(obj_type + ' notifications ' + on_off);
                msg.text(toTitleCase(obj_type) + ' notifications ' + on_off + '.');
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

function datatables_filterbox_shim(placeholder){
    /* Could there be a better name for this function and
    the hackery it inflicts? */

    // Select the existing filter box.
    var filter_box = $("#main-table_filter label input");
    filter_box = $(filter_box[0]);

    // Add some attributes.
    filter_box.attr('placeholder', placeholder);
    filter_box.attr('name', 'search_text');

    // Get its parent, then detach it.
    var filter_parent = filter_box.parent();
    filter_box.detach();

    // Wrap it in a form.
    var form = $('<form id="main-table_filter" class="colRt"></form>');
    form.prepend(filter_box);

    // Attach it again.
    var toggle_buttons = $("#toggleBtns");
    // toggle_buttons.addClass('sixCol');
    toggle_buttons.addClass('colLt');
    toggle_buttons.css('margin-right', '0px');
    form.insertAfter(toggle_buttons);

    // Nuke the data tables filter div.
    $('.dataTables_filter').remove();

}
