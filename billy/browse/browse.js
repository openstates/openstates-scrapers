var objects;

$(document).ready(function() {
    if (navigator.userAgent.indexOf('Gecko/') == -1) {
        $("#loading").html("The Open States Browser only supports Firefox.");
    } else {
        var types = {"legislators": populateLegislators,
                     "bills": populateBills,
                     "committees": populateCommittees,
                     "votes": populateVotes}

        $.each(types, function(type, populateFunc) {
            $("#" + type + "_button").click(function() {
                $("#obj_list_wrapper").hide();
                $("#loading").show();

                setTimeout(types[type], 0, [$("#state").val()]);
            });
        });

        setTimeout(populateLegislators, 0, [$("#state").val()]);
    }
});

function populateLegislators(state) {
    populate("/data/" + state + "/legislators",
             [{'name': "full_name"}, {'name': "first_name"},
              {'name': "last_name"}]);
}

function populateBills(state) {
    populate("/data/" + state + "/bills",
             [{'name': "bill_id"}, {'name': 'session'},
              {'name': 'chamber'}, {'name': "title"}]);
}

function populateCommittees(state) {
    populate("/data/" + state + "/committees",
             [{'name': 'committee'}, {'name': 'subcommittee'},
              {'name': 'chamber'}]);
}

function populateVotes(state) {
    populate("/data/" + state + '/votes',
             [{'name': 'bill_id'}, {'name': 'motion'}]);
}

function populate(dir, columns) {
    netscape.security.PrivilegeManager.enablePrivilege("UniversalXPConnect");

    objects = new Array();

    $("#obj_view").hide();

    var dir_path = window.location.pathname.split("/");
    dir_path = dir_path.splice(0, dir_path.length - 3).join('/') + dir;
    console.log(dir_path);

    var obj_list = document.createElement("table");

    var thead = document.createElement("thead");
    var tr = document.createElement("tr");
    for (var i in columns) {
        $(tr).append("<th class='sorting'>" + columns[i].name + "</th>");
    }
    $(thead).append(tr);
    $(obj_list).append(thead);

    var obj_paths = listing(dir_path);

    for (var i in obj_paths) {
        if (obj_paths[i].indexOf(".json") == -1) {
            continue;
        }

        var obj = JSON.parse($.twFile.load(obj_paths[i]));
        objects.push(obj);

        var tr = document.createElement("tr");

        for (var c in columns) {
            var column = columns[c];
            var value = obj[column.name];

            if (typeof value == "string") {
                value = "'" + value + "'"
            }

            if (c == 0) {
                $(tr).append("<td><a href='#" + value + "' onclick='view(" +
                             i + ")'>" + value + "</a></td>");
            } else {
                $(tr).append("<td>" + value + "</td>");
            }
        }

        $(obj_list).append(tr);
    }

    var dtCols = new Array(columns.length);
    for (var i in dtCols) {
        dtCols[i] = null;
    }
    dtCols[0] = {"sType": "html"};

    $(obj_list).attr("id", "obj_list");

    if ($("#obj_list_wrapper").length > 0) {
        $("#obj_list_wrapper").replaceWith(obj_list);
    } else {
        $("#obj_list").replaceWith(obj_list);
    }

    $(obj_list).dataTable({"aaSorting": [[0, "asc"]],
                           "aoColumns": dtCols,
                           "bAutoWidth": true,
                           "bPaginate": true,
                           "sPaginationType": "full_numbers"});


    $("#obj_list").show();
    $("#loading").hide();
}

function view(i) {
    var obj = objects[i];

    var pre = document.createElement("pre");
    $(pre).attr("id", "obj_text").html(JSON.stringify(obj, null, 2)).attr(
        "class", "prettyprint");
    $("#obj_text").replaceWith(pre);

    prettyPrint();

    $("#obj_view").show();
}

function listing(path) {
    netscape.security.PrivilegeManager.enablePrivilege("UniversalXPConnect");

    var directory = Components.classes[
        "@mozilla.org/file/local;1"].createInstance(
            Components.interfaces.nsILocalFile);

    directory.initWithPath(path);

    if (!directory.exists() || !directory.isDirectory()) {
        return null;
    }

    children = new Array();
    entries = directory.directoryEntries;
    while(entries.hasMoreElements()) {
        children.push(entries.getNext().QueryInterface(
            Components.interfaces.nsILocalFile).path);
    }

    return children;
}