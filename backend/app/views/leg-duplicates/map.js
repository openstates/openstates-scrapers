function(doc) {
    if(doc.type == 'legislator') {
        emit([doc.chamber, doc.district, doc.fullname], null);
    }
}
