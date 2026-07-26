'use strict';
'require view';
'require rpc';
'require dom';
'require poll';

var callStatus = rpc.declare({ object: 'athena', method: 'status' });
return view.extend({
	load: function() { return callStatus(); },
	render: function(s) {
		return E([], [
			E('h2', {}, _('Athena AX6600 状态')),
			E('div', { class: 'cbi-map' }, [
				E('p', {}, _('版本：') + (s.version || 'unknown')),
				E('p', {}, _('初始化状态：') + (s.setup_state || 'not initialized')),
				E('p', {}, _('DAED：') + (s.daed_running ? _('运行中') : _('安全关闭'))),
				E('p', {}, _('恢复入口：') + (s.recovery_url || 'http://192.168.50.1:8080/')),
				E('p', {}, _('IoT 网络：') + (s.iot_status || _('已禁用')))
			])
		]);
	},
	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
