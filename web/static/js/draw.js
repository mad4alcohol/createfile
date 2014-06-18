// Generated by CoffeeScript 1.7.1
(function() {
  var container, fc_container, fill_ct_text, fire_post, maybe, _data, _hide_loading, _show_loading,
    __slice = [].slice;

  container = document.getElementById('container');

  fc_container = document.getElementById('fc-container');

  _data = [];

  _show_loading = function() {
    $('ct-text').text('');
    $('#loading').show();
    return $('#ct-view').hide();
  };

  _hide_loading = function() {
    $('#loading').hide();
    return $('#ct-view').show();
  };

  _hide_loading();

  fill_ct_text = function(method) {
    var d, fp, segments, t, texts, tf, _d;
    if (method === 'time') {
      _d = _.sortBy(_data, function(i) {
        return i[1];
      });
    } else if (method === 'fc') {
      _d = _.sortBy(_data, function(i) {
        if (i.length > 2) {
          return parseInt(i[2][0]);
        } else {
          return 0;
        }
      });
    }
    texts = ((function() {
      var _i, _len, _results;
      _results = [];
      for (_i = 0, _len = _d.length; _i < _len; _i++) {
        d = _d[_i];
        fp = d[0], t = d[1], segments = 3 <= d.length ? __slice.call(d, 2) : [];
        if (segments.length === 0) {
          segments = 'empty cluster list';
        }
        tf = moment(Math.floor(t)).format('YYYY/MM/DD HH:mm:ss');
        _results.push("<li>" + tf + " " + fp + ": " + segments + "</li>");
      }
      return _results;
    })()).join('');
    return $('#ct-text').html(("<p>" + _d.length + " file(s) in total.</p>") + ("<ul>" + texts + "</ul>"));
  };

  $('#ctc-time').click(function() {
    return fill_ct_text('time');
  });

  $('#ctc-fc').click(function() {
    return fill_ct_text('fc');
  });

  maybe = function(n, d) {
    if (d == null) {
      d = 0;
    }
    if (n === '') {
      return d;
    } else {
      return n;
    }
  };

  fire_post = function() {
    var stream_uri;
    stream_uri = $('#stream-uri').val();
    _show_loading();
    return $.post('/cl', {
      stream_uri: stream_uri,
      deleted: $('#deleted').prop('checked'),
      regular: $('#regular').prop('checked'),
      datetime_start: moment(maybe($('#dt-start').val(), '0001-01-01 00:00:00:000'), 'YYYY-MM-DD HH:mm:ss:SSS').valueOf(),
      datetime_end: moment(maybe($('#dt-end').val(), '9999-12-31 23:59:59:999'), 'YYYY-MM-DD HH:mm:ss:SSS').valueOf(),
      cluster_start: maybe($('#cluster-start').val()),
      cluster_end: maybe($('#cluster-end').val(), Math.pow(2, 32)),
      use_cache: $('#use-cache').prop('checked')
    }, function(result) {
      var data, draw_fc_graph, draw_graph, fc_graph, fc_options, graph, idx_table, options, stream_title, _c_max, _c_min, _cl_fc, _cl_flattened;
      _hide_loading();
      data = result['files'];
      idx_table = result['idx_table'];
      _data = $.extend({}, data);
      data = _.map(data, function(l) {
        return l.slice(1);
      });
      _cl_fc = _.map(data, function(l) {
        return [l[0], l[1] != null ? l[1][0] : 0];
      });
      _cl_fc = _.sortBy(_cl_fc, function(i) {
        return i[0];
      });
      data = _.sortBy(data, function(i) {
        return i[0];
      });
      _cl_flattened = _.flatten(_.map(data, function(l) {
        return l.slice(1);
      }));
      _c_min = _.min(_cl_flattened);
      _c_max = _.max(_cl_flattened);
      stream_title = stream_uri === '' ? 'default stream' : stream_uri;
      options = {
        ct_view: {
          show: true,
          horizontal: false,
          shadowSize: 0.5,
          barWidth: 10,
          HtmlText: false,
          topPadding: 10
        },
        xaxis: {
          mode: 'time',
          noTicks: 12,
          labelsAngle: 45,
          autoscale: true
        },
        yaxis: {
          autoscale: true,
          min: _c_min,
          max: _c_max,
          margin: true
        },
        selection: {
          mode: 'xy'
        },
        title: "CT Plot - " + stream_title,
        mouse: {
          track: true,
          relative: true,
          trackFormatter: function(obj) {
            var date, path;
            date = moment(Math.floor(obj.x)).format('YYYY/MM/DD HH:mm:ss');
            path = idx_table[obj.x.toString()][obj.y[0].toString()];
            return "" + path + " ::= cl: " + obj.y + ", ts: " + date;
          }
        }
      };
      fc_options = {
        line: {
          show: true
        },
        xaxis: {
          mode: 'time',
          noTicks: 12,
          labelsAngle: 45,
          autoscale: true
        },
        yaxis: {
          autoscale: true,
          min: _c_min,
          max: _c_max,
          margin: true
        },
        selection: {
          mode: 'xy'
        },
        title: "FC Plot - " + stream_title
      };
      draw_graph = function(opts) {
        return Flotr.draw(container, [data], Flotr._.extend(Flotr._.clone(options), opts || {}));
      };
      draw_fc_graph = function(opts) {
        return Flotr.draw(fc_container, [_cl_fc], Flotr._.extend(Flotr._.clone(fc_options), opts || {}));
      };
      graph = draw_graph();
      fc_graph = draw_fc_graph();
      Flotr.EventAdapter.observe(container, 'flotr:select', function(area) {
        graph = draw_graph({
          xaxis: {
            min: area.x1,
            max: area.x2,
            mode: 'time',
            labelsAngle: 45
          },
          yaxis: {
            min: area.y1,
            max: area.y2
          }
        });
        return fc_graph = draw_fc_graph({
          xaxis: {
            min: area.x1,
            max: area.x2,
            mode: 'time',
            labelsAngle: 45
          },
          yaxis: {
            min: area.y1,
            max: area.y2
          }
        });
      });
      return Flotr.EventAdapter.observe(container, 'flotr:click', function() {
        graph = draw_graph();
        return fc_graph = draw_fc_graph();
      });
    });
  };

  $('#fire_post').click(fire_post);

  shortcut.add('enter', function() {
    return fire_post();
  });

}).call(this);

//# sourceMappingURL=draw.map
