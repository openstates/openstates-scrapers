var objects = new Array();

function populateLegislators(state) {
    populate("/data/" + state + "/legislators",
             [{'name': "full_name"}]);
}

function populateBills(state) {
    populate("/data/" + state + "/bills",
             [{'name': "bill_id"}, {'name': "title"}]);
}

function populate(dir, columns) {
    netscape.security.PrivilegeManager.enablePrivilege("UniversalXPConnect");
    
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
        var obj = JSON.parse($.twFile.load(obj_paths[i]));
        objects.push(obj);

        var tr = document.createElement("tr");

        for (var c in columns) {
            var column = columns[c];
            var value = obj[column.name];
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

    $(obj_list).attr("id", "obj_table");
    $("#obj_list").replaceWith(obj_list);

    $("#obj_list").dataTable({"aaSorting": [[0, "asc"]],
                              "aoColumns": dtCols,
                              "bAutoWidth": true});

    $("#obj_list").show();
}

function view(i) {
    var obj = objects[i];

    var pre = document.createElement("pre");
    $(pre).attr("id", "obj_text").html(JSON.stringify(obj, null, 2));
    $("#obj_text").replaceWith(pre);
    
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