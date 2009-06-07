// This map function can be used by itself to get a list of all of the
// members of each party serving in a given term/chamber, or to get a count
// of the number serving if combined with the given reduce function.
function(doc) {
    if(doc.type == 'legislator') {
        for(var i in doc.sessions) {
            emit([doc.party, doc.sessions[i], doc.chamber], doc.full_name);
        }
    }
}
