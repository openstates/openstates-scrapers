function(doc) {
    if(doc.type == 'legislator') {
        for(var  i in doc.sessions) {
            emit([doc.chamber, doc.district, doc.sessions[i]], null);
        }
    }
}
