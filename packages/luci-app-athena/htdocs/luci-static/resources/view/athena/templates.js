'use strict';
'require view';
'require rpc';
var callTemplates = rpc.declare({ object: 'athena', method: 'templates' });
return view.extend({
	load: function() { return callTemplates(); },
	render: function(data) {
		var nodes = [ E('h2', {}, _('DAED 配置模板')) ];
		Object.keys(data.files || {}).forEach(function(name) {
			nodes.push(E('h3', {}, name), E('pre', { class: 'athena-template' }, data.files[name]));
		});
		return E([], nodes);
	},
	handleSaveApply: null, handleSave: null, handleReset: null
});
