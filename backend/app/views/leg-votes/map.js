// This view takes a long time to compute!
function(doc) {
    if(doc.type != 'bill') {
        return;
    }

    for(var i in doc.votes) {
        var vote = doc.votes[i];
        
        for(var j in vote.yes_votes) {
            if(vote.yes_votes[j].leg_id) {
                emit([vote.yes_votes[j].leg_id, doc.session, doc._id],
                     {'vote': 'yes', 'bill_title': doc.title,
                             'motion': vote.motion});
            }
        }

        for(var j in vote.no_votes) {
            if(vote.no_votes[j].leg_id) {
                emit([vote.no_votes[j].leg_id, doc.session, doc._id],
                     {'vote': 'no', 'bill_title': doc.title,
                             'motion': vote.motion});
            }
        }

        for(var j in vote.other_votes) {
            if(vote.other_votes[j].leg_id) {
                emit([vote.other_votes[j].leg_id, doc.session, doc._id],
                     {'vote': 'other', 'bill_title': doc.title,
                             'motion': vote.motion});
            }
        }
    }
}
