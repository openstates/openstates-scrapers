// from couch.js
function encodeOptions(options) {
  var buf = []
  if (typeof(options) == "object" && options !== null) {
    for (var name in options) {
      if (!options.hasOwnProperty(name)) continue;
      var value = options[name];
      if (name == "key" || name == "startkey" || name == "endkey") {
        value = toJSON(value);
      }
      buf.push(encodeURIComponent(name) + "=" + encodeURIComponent(value));
    }
  }
  if (!buf.length) {
    return "";
  }
  return "?" + buf.join("&");
}

function concatArgs(array, args) {
  for (var i=0; i < args.length; i++) {
    array.push(args[i]);
  };
  return array;
};

function makePath(array) {
  var options, path;
  
  if (typeof array[array.length - 1] != "string") {
    // it's a params hash
    options = array.pop();
  }
  path = array.map(function(item) {return encodeURIComponent(item)}).join('/');
  if (options) {
    return path + encodeOptions(options);
  } else {
    return path;    
  }
};

function assetPath() {
  var p = req.path, parts = ['', p[0], p[1] , p[2]];
  return makePath(concatArgs(parts, arguments));
};

function showPath() {
  var p = req.path, parts = ['', p[0], p[1] , p[2], '_show'];
  return makePath(concatArgs(parts, arguments));
};

function listPath() {
  var p = req.path, parts = ['', p[0], p[1] , p[2], '_list'];
  return makePath(concatArgs(parts, arguments));
};

function olderPath(info) {
  if (!info) return null;
  var q = req.query;
  q.startkey = info.prev_key;
  q.skip=1;
  return listPath('index','recent-posts',q);
}

function makeAbsolute(req, path) {
  return 'http://' + req.headers.Host + path;
}
