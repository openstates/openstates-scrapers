function(doc) {
    if(doc.type == 'legislator') {
        for(var i in doc.sessions) {
            emit(doc.sessions[i], null);
        }
    }
}
