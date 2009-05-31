function(head, row, req) {
  respondWith(req, {
    html : function() {
      if (head) {
        return '<html><h1>Listing</h1> total rows: '+head.row_count+'<ul/>';
      } else if (row) {
        return '\n<li>Id:' + row.id + '</li>';
      } else {
        return '</ul></html>';
      }
    },
    xml : function() {
      if (head) {
        return {body:'<feed xmlns="http://www.w3.org/2005/Atom">'
          +'<title>Test XML Feed</title>'};
      } else if (row) {
        // Becase Safari can't stand to see that dastardly
        // E4X outside of a string. Outside of tests you
        // can just use E4X literals.
        var entry = new XML('<entry/>');
        entry.id = row.id;
        entry.title = row.key;
        entry.content = row.value;
        return {body:entry};
      } else {
        return {body : "</feed>"};
      }
    }
  })
};