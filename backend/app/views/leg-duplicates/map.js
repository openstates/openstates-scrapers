function(doc) {
    if(doc.type == 'legislator') {
        emit([doc.chamber, doc.district, doc.full_name], null);
    }
}
