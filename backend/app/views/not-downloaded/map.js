// Get a list of bill versions that have not been downloaded.
function(doc) {
    if(doc.type != 'bill') {
        return;
    }

    for(var i in doc.versions) {
        var url = doc.versions[i].url;
        var path = url.replace('http://', '/').replace('ftp://', '/')

        if(!doc._attachments || !doc._attachments[path]) {
            emit([doc._id, doc._rev], url);
        }
    }
}
