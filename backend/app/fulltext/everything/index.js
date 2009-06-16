function(doc) {
    if(doc.type == 'bill') {
        var ret = new Document();
        ret.add('bill', {"field": "type", "store": "yes"});
        ret.add(doc.title, {"field": "title", "store": "yes"});
        ret.add(doc.bill_id, {"field": "bill_id", "store": "yes"});
        ret.add(doc.session, {"field": "session", "store": "yes"});
        return ret;
    } else if(doc.type == 'legislator') {
        var ret = new Document();
        ret.add('legislator', {"field": "type", "store": "yes"});
        ret.add(doc.full_name, {"field": "full_name", "store": "yes"});
        ret.add(doc.party, {"field": "party", "store": "yes"});
        ret.add(doc.district, {"field": "district", "store": "yes"});
        return ret;
    }
}
