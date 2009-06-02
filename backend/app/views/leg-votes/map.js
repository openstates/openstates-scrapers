function(doc) {
    if(doc.type != 'bill') {
        return;
    }

    for(var i in doc.votes) {
        var vote = doc.votes[i];
        
        for(var j in vote.yes_votes) {
            if(vote.yes_votes[j].leg_id) {
                emit([vote.yes_votes[j].leg_id, doc.session, 'yes'],
                     [doc._id, vote.motion]);
            }
        }

        for(var j in vote.no_votes) {
            if(vote.no_votes[j].leg_id) {
                emit([vote.no_votes[j].leg_id, doc.session, 'no'],
                     [doc._id, vote.motion]);
            }
        }

        for(var j in vote.other_votes) {
            if(vote.other_votes[j].leg_id) {
                emit([vote.other_votes[j].leg_id, doc.session, 'other'],
                     [doc._id, vote.motion]);
            }
        }
    }
}
