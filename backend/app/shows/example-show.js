function(doc, req) {
  // !code lib/helpers/template.js
  // !json lib.templates
  
  respondWith(req, {
    html : function() {
      var html = template(lib.templates.example, doc);
      return {body:html}
    },
    xml : function() {
      return {
        body : <xml><node value={doc.title}/></xml>
      }
    }
  })
};