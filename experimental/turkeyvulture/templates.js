(function(undefined) {
  var global = this;
  var _templatetk = global.templatetk;

  /* an aweful method to exploit the browser's support for escaping HTML */
  var _escapeMapping = {
    '&':    '&amp;',
    '>':    '&gt;',
    '<':    '&lt;',
    "'":    '&#39;',
    '"':    '&#34;'
  };
  function escapeString(value) {
    return ('' + value).replace(/(["'&<>])/g, function(match) {
      return _escapeMapping[match[0]];
    });
  }

  function makeWriteFunc(buffer) {
    if (buffer.push.bind)
      return buffer.push.bind(buffer);
    return function(x) { buffer.push(x); };
  }

  function Config() {
    this.filters = {};
  };
  Config.prototype = {
    getAutoEscapeDefault : function(templateName) {
      return true;
    },

    getFilters : function() {
      // TODO: make a copy here
      return this.filters;
    },

    evaluateTemplate : function(template, context, writeFunc, info) {
      template.run(template.makeRuntimeState(context, writeFunc, info));
    },

    getTemplate : function(name) {
      throw new Exception('Template loading not implemented');
    },

    joinPath : function(name, parent) {
      return name;
    }
  };

  function Context(vars, parent) {
    this.vars = vars;
    this.parent = parent;
  };
  Context.prototype = {
    lookup : function(name) {
      var rv = this.vars[name];
      if (this.parent && rv === undefined)
        return this.parent.lookup(name);
      return rtlib.makeUndefined(rv, name);
    }
  };

  function Template(rootFunc, setupFunc, blocks, config) {
    this.rootFunc = rootFunc;
    this.setupFunc = setupFunc;
    this.blocks = blocks;
    this.config = config;
    this.name = '<string>';
  };
  Template.prototype = {
    render : function(context) {
      context = new Context(context || {}, new Context(rtlib.getGlobals()));
      var buffer = [];
      var rtstate = this.makeRuntimeState(context, makeWriteFunc(buffer));
      this.run(rtstate);
      return buffer.join("");
    },

    _resolveSelector : function(container, selector) {
      if (selector != null)
        return jQuery(selector, container)[0].childNodes;
      return container.childNodes;
    },

    renderToElements : function(context, selector) {
      var container = document.createElement('div');
      container.innerHTML = this.render(context);
      return this._resolveSelector(container, selector);
    },

    renderInto : function(context, targetSelector, selector) {
      var elements = this.renderToElements(context, selector);
      jQuery(targetSelector).empty().append(elements);
    },

    replaceRender : function(context, selectors) {
      var container = document.createElement('div');
      container.innerHTML = this.render(context);
      if (typeof selectors === 'string')
        this._replaceWithSelector(container, selectors);
      for (var i = 0, n = selectors.length; i < n; i++)
        this._replaceWithSelector(container, selectors[i]);
    },

    _replaceWithSelector : function(container, selector) {
      var elements = this._resolveSelector(container, selector);
      jQuery(selector).empty().append(elements);
    },

    makeRuntimeState : function(context, writeFunc, info) {
      return new rtlib.RuntimeState(context, writeFunc, this.config, this.name, info);
    },

    run : function(rtstate) {
      this.setupFunc(rtstate);
      this.rootFunc(rtstate);
    },

    toString : function() {
      if (this.name == null)
        return '[Template]';
      return '[Template "' + this.name + '"]';
    }
  };

  var RuntimeState = function(context, writeFunc, config, templateName, info) {
    this.context = context;
    this.config = config;
    this.writeFunc = writeFunc;
    this.buffers = [];
    if (!info)
      info = new rtlib.RuntimeInfo(this.config, templateName);
    this.info = info;
  };
  RuntimeState.prototype = {
    lookupVar : function(name) {
      return this.context.lookup(name);
    },

    makeOverlayContext : function(locals) {
      return new Context(locals, this.context);
    },

    evaluateBlock : function(name, context, level) {
      if (level === undefined)
        level = -1;
      return this.info.evaluateBlock(name, level, context, this.writeFunc);
    },

    exportVar : function(name, value) {
      this.info.exports[name] = value;
    },

    getTemplate : function(name) {
      var templateName = this.config.joinPath(name, this.templateName);
      var tmpl = this.info.templateCache[templateName];
      if (tmpl != null)
        return tmpl;
      var rv = this.config.getTemplate(templateName);
      this.info.templateCache[templateName] = rv;
      return rv;
    },

    extendTemplate : function(name, context, writeFunc) {
      var template = this.getTemplate(name);
      var info = this.info.makeInfo(template, name, "extends");
      return this.config.evaluateTemplate(template, context, writeFunc, info);
    },

    startBuffering : function() {
      var buffer = [];
      this.buffers.push([this.writeFunc, buffer]);
      return this.writeFunc = makeWriteFunc(buffer);
    },

    endBuffering : function() {
      var entry = this.buffers.pop();
      this.writeFunc = entry[0];
      var rv = entry[1].join('');
      if (this.autoescape)
        rv = rtlib.markSafe(rv);
      return [this.writeFunc, rv];
    }
  };

  var RuntimeInfo = function(config, templateName) {
    this.config = config;
    this.templateName = templateName;
    this.autoescape = config.getAutoEscapeDefault(templateName);
    this.filters = config.getFilters();
    this.blockExecutors = {};
    this.templateCache = {};
    this.exports = {};
  }
  RuntimeInfo.prototype = {
    evaluateBlock : function(name, level, vars, writeFunc) {
      var executors = this.blockExecutors[name];
      var func = executors[~level];
      return func(this, vars, writeFunc);
    },

    callFilter : function(filterName, obj, args) {
      var func = this.filters[filterName];
      return func.apply(obj, args);
    },

    makeInfo : function(template, templateName, behavior) {
      var rv = new RuntimeInfo(this.config, templateName);
      rv.templateCache = this.templateCache;
      if (behavior === 'extends')
        for (var key in this.blockExecutors)
          rv.blockExecutors[key] = this.blockExecutors[key];
      return rv;
    },

    finalize : function(value) {
      return rtlib.finalize(value, this.autoescape);
    },

    registerBlock : function(name, executor) {
      var m = this.blockExecutors;
      (m[name] = (m[name] || [])).push(executor);
    }
  };

  var rtlib = {
    Template : Template,
    RuntimeState : RuntimeState,
    RuntimeInfo : RuntimeInfo,

    makeUndefined : function(value, name) {
      return value;
    },

    getConfig : function() {
      return lib.config;
    },

    getGlobals : function() {
      return lib.globals;
    },

    registerBlockMapping : function(info, blocks) {
      for (var name in blocks)
        info.registerBlock(name, (function(renderFunc) {
          return function(info, vars, writeFunc) {
            return renderFunc(new rtlib.RuntimeState(vars, writeFunc, info.config,
              info.templateName));
          };
        })(blocks[name]));
    },

    makeTemplate : function(rootFunc, setupFunc, blocks) {
      return new this.Template(rootFunc, setupFunc, blocks, this.getConfig());
    },

    sequenceFromIterable : function(iterable) {
      if (!iterable)
        return [];
      if (iterable.length !== undefined)
        return iterable;
      return this.sequenceFromObject(iterable);
    },

    sequenceFromObject : function(obj) {
      var rv = [];
      for (var key in obj)
        rv.push(key);
      return rv;
    },

    unpackTuple : function(obj, unpackInfo, loopContext) {
      var rv = [null];
      function unpack(obj, info) {
        for (var i = 0, n = info.length; i < n; i++)
          if (typeof info[i] !== 'string')
            unpack(obj[i], info[i]);
          else
            rv.push(rtlib.makeUndefined(obj[i], info[i]));
      }
      unpack(obj, unpackInfo);
      return rv;
    },

    markSafe : function(value) {
      return value;
    },

    concat : function(info, pieces) {
      return ''.join(pieces);
    },

    finalize : function(value, autoescape) {
      return '' + value;
    },

    iterate : function(iterable, parent, unpackInfo, func, elseFunc) {
      var seq = rtlib.sequenceFromIterable(iterable);
      var n = seq.length;
      var ctx = {
        parent:     parent,
        first:      true,
        index0:     0,
        index:      1,
        revindex:   n,
        revindex0:  n - 1,
        cycle:      function() {
          return arguments[ctx.index0 % arguments.length];
        }
      };
      var simple = unpackInfo.length == 1 && typeof unpackInfo[0] === 'string';
      for (var i = 0; i < n; i++) {
        ctx.last = i + 1 == n;
        if (simple)
          func(ctx, rtlib.makeUndefined(seq[i], unpackInfo[0]));
        else
          func.apply(null, rtlib.unpackTuple(seq[i], unpackInfo, ctx));
        ctx.first = false;
        ctx.index0++, ctx.index++;
        ctx.revindex--, ctx.revindex0--;
      }
      if (ctx.index0 == 0 && elseFunc)
        elseFunc();
    },

    wrapFunction : function(name, argNames, defaults, func) {
      var argCount = argNames.length;
      return function() {
        var args = [];
        for (var i = 0, n = Math.min(arguments.length, argCount); i < n; i++)
          args.push(arguments[i]);
        var off = args.length;
        if (off != argCount)
          for (var i = 0, n = argCount - off; i < n; i++) {
            var didx = defaults.length + (i - argCount + off);
            args.push(rtlib.makeUndefined(defaults[didx], argNames[off + i]));
          }
        return func.apply(null, args);
      };
    }
  };


  var lib = global.templatetk = {
    config : new Config(),
    globals : {},
    Config : Config,
    rt : rtlib,
    utils : {
      escape : escapeString
    },
    noConflict : function() {
      global.templatetk = _templatetk;
      return lib;
    }
  };
})();
(function() {
  var global = this;
  var _jsonjinja = global.jsonjinja;
  var templatetk = global.templatetk.noConflict();
  var hasOwnProperty = Object.prototype.hasOwnProperty;

  templatetk.config.getTemplate = function(name) {
    return lib.getTemplate(name);
  };

  templatetk.config.getAutoEscapeDefault = function(name) {
    return !!name.match(/\.(html|xml)$/);
  };

  templatetk.rt.sequenceFromObject = function(obj) {
    var rv = [];
    for (var key in obj)
      if (hasOwnProperty.call(obj, key))
        rv.push([key, obj[key]]);
    rv.sort();
    return rv;
  };

  templatetk.rt.markSafe = function(value) {
    return {__jsonjinja_wire__: 'html-safe', value: value};
  };

  templatetk.rt.concat = function(info, pieces) {
    var rv = [];
    for (var i = 0, n = pieces.length; i != n; i++)
      rv.push(info.finalize(pieces[i]));
    rv = rv.join('');
    return info.autoescape ? this.markSafe(rv) : rv;
  };

  templatetk.rt.finalize = function(value, autoescape) {
    if (value == null)
      return '';
    if (typeof value === 'boolean' ||
        typeof value === 'number')
      return '' + value;
    var wod = lib.grabWireObjectDetails(value);
    if (wod === 'html-safe')
      return value.value;
    if (value instanceof Array ||
        (value.prototype && value.prototype.toString === Object.prototype.toString))
      lib.signalError('Cannot print complex objects, tried to print ' +
        Object.prototype.toString.call(value) + ' (' + value + ')');
    if (autoescape)
      return templatetk.utils.escape(value);
    return '' + value;
  };

  var lib = global.jsonjinja = {
    _templateFactories : {},
    _templates : {},

    grabWireObjectDetails : function(object) {
      if (object && typeof object.__jsonjinja_wire__ !== 'undefined')
        return object.__jsonjinja_wire__;
      return null;
    },

    getTemplate : function(name) {
      var tmpl = this._templates[name];
      if (tmpl == null) {
        var factory = this._templateFactories[name];
        if (factory == null)
          return null;
        tmpl = this._registerTemplate(name, factory(templatetk.rt));
      }
      return tmpl;
    },

    addTemplate : function(name, factoryOrTemplate) {
      if (factoryOrTemplate instanceof templatetk.rt.Template) {
        this._registerTemplate(name, factoryOrTemplate);
      } else {
        this._templates[name] = null;
        this._templateFactories[name] = factoryOrTemplate;
      }
    },

    _registerTemplate : function(name, template) {
      delete this._templateFactories[name];
      this._templates[name] = template;
      template.name = name;
      return template;
    },

    removeTemplate : function(name) {
      delete this._templates[name];
      delete this._templateFactories[name];
    },

    listTemplates : function() {
      var rv = [];
      for (var key in this._templates)
        rv.push(key);
      rv.sort();
      return rv;
    },

    addTemplates : function(mapping) {
      for (var key in mapping)
        this.addTemplate(key, mapping[key]);
    },

    templatetk : templatetk,

    signalError : function(message) {
      if (console && console.error)
        console.error(message);
    },

    noConflict : function() {
      global.jsonjinja = _jsonjinja;
      return lib;
    }
  };
})();

jsonjinja.addTemplates(
{"bill_1.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["bill"], function(l_loop_0, l_bill_0) {
      var l_loop_1 = rts.lookupVar("loop"), l_loop_2 = rts.lookupVar("loop"), l_loop_3 = rts.lookupVar("loop"), l_bill_0, l_loop_0;
      w("\n        <li>\n        <i class='icon-file'></i>\n        <h3>\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_bill_0["state"]));
      w("/bills/");
      w(rts.info.finalize(l_bill_0["session"]));
      w("/");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("'>\n            ");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("\n            </a>\n        </h3>\n        <p>");
      w(rts.info.finalize(l_bill_0["title"]));
      w("</p>\n        <p>\n        ");
      rt.iterate(l_bill_0["type"], l_loop_0, ["subject"], function(l_loop_1, l_subject_0) {
        var l_loop_1, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["subjects"], l_loop_0, ["subject"], function(l_loop_2, l_subject_0) {
        var l_loop_2, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["scraped_subjects"], l_loop_0, ["subject"], function(l_loop_3, l_subject_0) {
        var l_loop_3, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        </p>\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"bill_2.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["bill"], function(l_loop_0, l_bill_0) {
      var l_loop_1 = rts.lookupVar("loop"), l_loop_2 = rts.lookupVar("loop"), l_loop_3 = rts.lookupVar("loop"), l_bill_0, l_loop_0;
      w("\n        <li>\n        <i class='icon-file'></i>\n        <h3>\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_bill_0["state"]));
      w("/bills/");
      w(rts.info.finalize(l_bill_0["session"]));
      w("/");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("'>\n            ");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("\n            </a>\n        </h3>\n        <p>");
      w(rts.info.finalize(l_bill_0["title"]));
      w("</p>\n        <p>\n        ");
      rt.iterate(l_bill_0["type"], l_loop_0, ["subject"], function(l_loop_1, l_subject_0) {
        var l_loop_1, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["subjects"], l_loop_0, ["subject"], function(l_loop_2, l_subject_0) {
        var l_loop_2, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["scraped_subjects"], l_loop_0, ["subject"], function(l_loop_3, l_subject_0) {
        var l_loop_3, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        </p>\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"bill_3.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["bill"], function(l_loop_0, l_bill_0) {
      var l_loop_1 = rts.lookupVar("loop"), l_loop_2 = rts.lookupVar("loop"), l_loop_3 = rts.lookupVar("loop"), l_bill_0, l_loop_0;
      w("\n        <li>\n        <i class='icon-file'></i>\n        <h3>\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_bill_0["state"]));
      w("/bills/");
      w(rts.info.finalize(l_bill_0["session"]));
      w("/");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("'>\n            ");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("\n            </a>\n        </h3>\n        <p>");
      w(rts.info.finalize(l_bill_0["title"]));
      w("</p>\n        <p>\n        ");
      rt.iterate(l_bill_0["type"], l_loop_0, ["subject"], function(l_loop_1, l_subject_0) {
        var l_loop_1, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["subjects"], l_loop_0, ["subject"], function(l_loop_2, l_subject_0) {
        var l_loop_2, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["scraped_subjects"], l_loop_0, ["subject"], function(l_loop_3, l_subject_0) {
        var l_loop_3, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        </p>\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"bill_4.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["bill"], function(l_loop_0, l_bill_0) {
      var l_loop_1 = rts.lookupVar("loop"), l_loop_2 = rts.lookupVar("loop"), l_loop_3 = rts.lookupVar("loop"), l_bill_0, l_loop_0;
      w("\n        <li>\n        <i class='icon-file'></i>\n        <h3>\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_bill_0["state"]));
      w("/bills/");
      w(rts.info.finalize(l_bill_0["session"]));
      w("/");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("'>\n            ");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("\n            </a>\n        </h3>\n        <p>");
      w(rts.info.finalize(l_bill_0["title"]));
      w("</p>\n        <p>\n        ");
      rt.iterate(l_bill_0["type"], l_loop_0, ["subject"], function(l_loop_1, l_subject_0) {
        var l_loop_1, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["subjects"], l_loop_0, ["subject"], function(l_loop_2, l_subject_0) {
        var l_loop_2, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["scraped_subjects"], l_loop_0, ["subject"], function(l_loop_3, l_subject_0) {
        var l_loop_3, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        </p>\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"bill_5.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["bill"], function(l_loop_0, l_bill_0) {
      var l_loop_1 = rts.lookupVar("loop"), l_loop_2 = rts.lookupVar("loop"), l_loop_3 = rts.lookupVar("loop"), l_bill_0, l_loop_0;
      w("\n        <li>\n        <i class='icon-file'></i>\n        <h3>\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_bill_0["state"]));
      w("/bills/");
      w(rts.info.finalize(l_bill_0["session"]));
      w("/");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("'>\n            ");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("\n            </a>\n        </h3>\n        <p>");
      w(rts.info.finalize(l_bill_0["title"]));
      w("</p>\n        <p>\n        ");
      rt.iterate(l_bill_0["type"], l_loop_0, ["subject"], function(l_loop_1, l_subject_0) {
        var l_loop_1, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["subjects"], l_loop_0, ["subject"], function(l_loop_2, l_subject_0) {
        var l_loop_2, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["scraped_subjects"], l_loop_0, ["subject"], function(l_loop_3, l_subject_0) {
        var l_loop_3, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        </p>\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"bill_6-10.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["bill"], function(l_loop_0, l_bill_0) {
      var l_loop_1 = rts.lookupVar("loop"), l_loop_2 = rts.lookupVar("loop"), l_loop_3 = rts.lookupVar("loop"), l_bill_0, l_loop_0;
      w("\n        <li>\n        <i class='icon-file'></i>\n        <h3>\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_bill_0["state"]));
      w("/bills/");
      w(rts.info.finalize(l_bill_0["session"]));
      w("/");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("'>\n            ");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("\n            </a>\n        </h3>\n        <p>");
      w(rts.info.finalize(l_bill_0["title"]));
      w("</p>\n        <p>\n        ");
      rt.iterate(l_bill_0["type"], l_loop_0, ["subject"], function(l_loop_1, l_subject_0) {
        var l_loop_1, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["subjects"], l_loop_0, ["subject"], function(l_loop_2, l_subject_0) {
        var l_loop_2, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["scraped_subjects"], l_loop_0, ["subject"], function(l_loop_3, l_subject_0) {
        var l_loop_3, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        </p>\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"bill_6.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["bill"], function(l_loop_0, l_bill_0) {
      var l_loop_1 = rts.lookupVar("loop"), l_loop_2 = rts.lookupVar("loop"), l_loop_3 = rts.lookupVar("loop"), l_bill_0, l_loop_0;
      w("\n        <li>\n        <i class='icon-file'></i>\n        <h3>\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_bill_0["state"]));
      w("/bills/");
      w(rts.info.finalize(l_bill_0["session"]));
      w("/");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("'>\n            ");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("\n            </a>\n        </h3>\n        <p>");
      w(rts.info.finalize(l_bill_0["title"]));
      w("</p>\n        <p>\n        ");
      rt.iterate(l_bill_0["type"], l_loop_0, ["subject"], function(l_loop_1, l_subject_0) {
        var l_loop_1, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["subjects"], l_loop_0, ["subject"], function(l_loop_2, l_subject_0) {
        var l_loop_2, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["scraped_subjects"], l_loop_0, ["subject"], function(l_loop_3, l_subject_0) {
        var l_loop_3, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        </p>\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"bill_7.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["bill"], function(l_loop_0, l_bill_0) {
      var l_loop_1 = rts.lookupVar("loop"), l_loop_2 = rts.lookupVar("loop"), l_loop_3 = rts.lookupVar("loop"), l_bill_0, l_loop_0;
      w("\n        <li>\n        <i class='icon-file'></i>\n        <h3>\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_bill_0["state"]));
      w("/bills/");
      w(rts.info.finalize(l_bill_0["session"]));
      w("/");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("'>\n            ");
      w(rts.info.finalize(l_bill_0["bill_id"]));
      w("\n            </a>\n        </h3>\n        <p>");
      w(rts.info.finalize(l_bill_0["title"]));
      w("</p>\n        <p>\n        ");
      rt.iterate(l_bill_0["type"], l_loop_0, ["subject"], function(l_loop_1, l_subject_0) {
        var l_loop_1, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["subjects"], l_loop_0, ["subject"], function(l_loop_2, l_subject_0) {
        var l_loop_2, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        ");
      rt.iterate(l_bill_0["scraped_subjects"], l_loop_0, ["subject"], function(l_loop_3, l_subject_0) {
        var l_loop_3, l_subject_0;
        w("\n            <span class='label'>");
        w(rts.info.finalize(l_subject_0));
        w("</span>\n        ");
      }, null);
      w("\n        </p>\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"bill_base.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"bills_5.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"committee_1.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["c"], function(l_loop_0, l_c_0) {
      var l_c_0, l_loop_0;
      w("\n        <i class='icon-lock'></i>\n        <li><h3>\n            [");
      w(rts.info.finalize(l_c_0["chamber"]));
      w("]\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_c_0["state"]));
      w("/committees/");
      w(rts.info.finalize(l_c_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_c_0["committee"]));
      w("</a>\n        </h3></li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"committee_2.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["c"], function(l_loop_0, l_c_0) {
      var l_loop_1 = rts.lookupVar("loop"), l_c_0, l_loop_0;
      w("\n        <i class='icon-lock'></i>\n        <li><h3>\n            [");
      w(rts.info.finalize(l_c_0["chamber"]));
      w("]\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_c_0["state"]));
      w("/committees/");
      w(rts.info.finalize(l_c_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_c_0["committee"]));
      w("</a>\n            <div>\n                ");
      rt.iterate(l_c_0["members"], l_loop_0, ["member"], function(l_loop_1, l_member_0) {
        var l_member_0, l_loop_1;
        w("\n                    ");
        w(rts.info.finalize(l_member_0["name"]));
        w("\n                ");
      }, null);
      w("\n            </div>\n        </h3></li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"committee_3.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["c"], function(l_loop_0, l_c_0) {
      var l_c_0, l_loop_0;
      w("\n        <i class='icon-lock'></i>\n        <li><h3>\n            [");
      w(rts.info.finalize(l_c_0["chamber"]));
      w("]\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_c_0["state"]));
      w("/committees/");
      w(rts.info.finalize(l_c_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_c_0["committee"]));
      w("</a>\n        </h3></li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"committee_4.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["c"], function(l_loop_0, l_c_0) {
      var l_c_0, l_loop_0;
      w("\n        <i class='icon-lock'></i>\n        <li><h3>\n            [");
      w(rts.info.finalize(l_c_0["chamber"]));
      w("]\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_c_0["state"]));
      w("/committees/");
      w(rts.info.finalize(l_c_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_c_0["committee"]));
      w("</a>\n        </h3></li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"committee_5.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["c"], function(l_loop_0, l_c_0) {
      var l_c_0, l_loop_0;
      w("\n        <i class='icon-lock'></i>\n        <li><h3>\n            [");
      w(rts.info.finalize(l_c_0["chamber"]));
      w("]\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_c_0["state"]));
      w("/committees/");
      w(rts.info.finalize(l_c_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_c_0["committee"]));
      w("</a>\n        </h3></li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"committee_6-10.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["c"], function(l_loop_0, l_c_0) {
      var l_c_0, l_loop_0;
      w("\n        <i class='icon-lock'></i>\n        <li><h3>\n            [");
      w(rts.info.finalize(l_c_0["chamber"]));
      w("]\n            <a href='http://openstates.org/");
      w(rts.info.finalize(l_c_0["state"]));
      w("/committees/");
      w(rts.info.finalize(l_c_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_c_0["committee"]));
      w("</a>\n        </h3></li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"committee_base.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"layout_0.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    w("No results :(");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"layout_0_col.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"layout_1_col.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_col1_0 = rts.lookupVar("col1");
    w("    <div class=\"row-fluid show-grid\">\n        <div class=\"span12\">\n            ");
    w(rts.info.finalize(l_col1_0));
    w("\n        </div>\n    </div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"layout_2_col.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_col1_0 = rts.lookupVar("col1"), l_col2_0 = rts.lookupVar("col2");
    w("    <div class=\"row-fluid show-grid\">\n        <div class=\"span6\">\n            ");
    w(rts.info.finalize(l_col1_0));
    w("\n        </div>\n        <div class=\"span6\">\n            ");
    w(rts.info.finalize(l_col2_0));
    w("\n        </div>\n    </div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"layout_3_col.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_col1_0 = rts.lookupVar("col1"), l_col2_0 = rts.lookupVar("col2"), l_col3_0 = rts.lookupVar("col3");
    w("        <div class=\"span4\">\n            ");
    w(rts.info.finalize(l_col1_0));
    w("\n        </div>\n        <div class=\"span4\">\n            ");
    w(rts.info.finalize(l_col2_0));
    w("\n        </div>\n        <div class=\"span4\">\n            ");
    w(rts.info.finalize(l_col3_0));
    w("\n        </div>\n    </div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"legislator_base.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_person_0 = rts.lookupVar("person");
    w("<div>\n");
    if (l_person_0["length"]) { 
      var l_loop_0 = rts.lookupVar("loop"), l_person_count_0 = rts.lookupVar("person_count");
      w("\n<h2>Legislators (");
      w(rts.info.finalize(l_person_count_0));
      w(")</h2>\n<ul>\n");
      rt.iterate(l_person_0, l_loop_0, ["leg"], function(l_loop_0, l_leg_0) {
        var l_loop_0, l_leg_0;
        w("\n    <li>\n    <div class='content'>\n    <i class='icon-user'></i>\n    <h3>\n        [");
        w(rts.info.finalize(l_leg_0["chamber"]));
        w("] <a href='http://openstates.org/");
        w(rts.info.finalize(l_leg_0["state"]));
        w("/legislators/");
        w(rts.info.finalize(l_leg_0["_id"]));
        w("/'>");
        w(rts.info.finalize(l_leg_0["full_name"]));
        w("</a>\n    </h3> (");
        w(rts.info.finalize(l_leg_0["party"]));
        w("--");
        w(rts.info.finalize(l_leg_0["district"]));
        w(")\n    </div>\n    </li>\n");
      }, null);
      w("\n</ul>\n");
    } else {
      var l_loop_0 = rts.lookupVar("loop"), l_person_count_0 = rts.lookupVar("person_count");
      w("\n <h2>No Legislators Found</h2>\n");
    }
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"person_1.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["leg"], function(l_loop_0, l_leg_0) {
      var l_loop_0, l_leg_0;
      w("\n        <li>\n        <i class='icon-user'></i>\n        <h3>\n            [");
      w(rts.info.finalize(l_leg_0["chamber"]));
      w("] <a href='http://openstates.org/");
      w(rts.info.finalize(l_leg_0["state"]));
      w("/legislators/");
      w(rts.info.finalize(l_leg_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_leg_0["full_name"]));
      w("</a>\n        </h3> (");
      w(rts.info.finalize(l_leg_0["party"]));
      w("--");
      w(rts.info.finalize(l_leg_0["district"]));
      w(")\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"person_2.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["leg"], function(l_loop_0, l_leg_0) {
      var l_loop_0, l_leg_0;
      w("\n        <li>\n        <i class='icon-user'></i>\n        <h3>\n            [");
      w(rts.info.finalize(l_leg_0["chamber"]));
      w("] <a href='http://openstates.org/");
      w(rts.info.finalize(l_leg_0["state"]));
      w("/legislators/");
      w(rts.info.finalize(l_leg_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_leg_0["full_name"]));
      w("</a>\n        </h3> (");
      w(rts.info.finalize(l_leg_0["party"]));
      w("--");
      w(rts.info.finalize(l_leg_0["district"]));
      w(")\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"person_3.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["leg"], function(l_loop_0, l_leg_0) {
      var l_loop_0, l_leg_0;
      w("\n        <li>\n        <img src=\"");
      w(rts.info.finalize(l_leg_0["photo_url"]));
      w("\">\n        <h3>\n            [");
      w(rts.info.finalize(l_leg_0["chamber"]));
      w("] <a href='http://openstates.org/");
      w(rts.info.finalize(l_leg_0["state"]));
      w("/legislators/");
      w(rts.info.finalize(l_leg_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_leg_0["full_name"]));
      w("</a>\n        </h3> (");
      w(rts.info.finalize(l_leg_0["party"]));
      w("--");
      w(rts.info.finalize(l_leg_0["district"]));
      w(")\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"person_4.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["leg"], function(l_loop_0, l_leg_0) {
      var l_loop_0, l_leg_0;
      w("\n        <li>\n        <i class='icon-user'></i>\n        <h3>\n            [");
      w(rts.info.finalize(l_leg_0["chamber"]));
      w("] <a href='http://openstates.org/");
      w(rts.info.finalize(l_leg_0["state"]));
      w("/legislators/");
      w(rts.info.finalize(l_leg_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_leg_0["full_name"]));
      w("</a>\n        </h3> (");
      w(rts.info.finalize(l_leg_0["party"]));
      w("--");
      w(rts.info.finalize(l_leg_0["district"]));
      w(")\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"person_5.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["leg"], function(l_loop_0, l_leg_0) {
      var l_loop_0, l_leg_0;
      w("\n        <li>\n        <i class='icon-user'></i>\n        <h3>\n            [");
      w(rts.info.finalize(l_leg_0["chamber"]));
      w("] <a href='http://openstates.org/");
      w(rts.info.finalize(l_leg_0["state"]));
      w("/legislators/");
      w(rts.info.finalize(l_leg_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_leg_0["full_name"]));
      w("</a>\n        </h3> (");
      w(rts.info.finalize(l_leg_0["party"]));
      w("--");
      w(rts.info.finalize(l_leg_0["district"]));
      w(")\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
}),"person_6-10.html":(function(rt) {
  function root(rts) {
    var w = rts.writeFunc;
    var l_loop_0 = rts.lookupVar("loop"), l_count_0 = rts.lookupVar("count"), l_objects_0 = rts.lookupVar("objects"), l_object_type_0 = rts.lookupVar("object_type");
    w("<div class='content'>\n    <h2>");
    w(rts.info.finalize(l_object_type_0));
    w("s (");
    w(rts.info.finalize(l_count_0));
    w(")</h2>\n    <ul>\n    ");
    rt.iterate(l_objects_0, l_loop_0, ["leg"], function(l_loop_0, l_leg_0) {
      var l_loop_0, l_leg_0;
      w("\n        <li>\n        <i class='icon-user'></i>\n        <h3>\n            [");
      w(rts.info.finalize(l_leg_0["chamber"]));
      w("] <a href='http://openstates.org/");
      w(rts.info.finalize(l_leg_0["state"]));
      w("/legislators/");
      w(rts.info.finalize(l_leg_0["_id"]));
      w("/'>");
      w(rts.info.finalize(l_leg_0["full_name"]));
      w("</a>\n        </h3> (");
      w(rts.info.finalize(l_leg_0["party"]));
      w("--");
      w(rts.info.finalize(l_leg_0["district"]));
      w(")\n        </li>\n    ");
    }, null);
    w("\n    </ul>\n</div>");
  }
  function setup(rts) {
    rt.registerBlockMapping(rts.info, blocks);
  }
  var blocks = {};
  return rt.makeTemplate(root, setup, blocks);
})});
