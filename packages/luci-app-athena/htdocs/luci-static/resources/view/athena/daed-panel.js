'use strict';
'require view';
'require rpc';
var callStatus = rpc.declare({ object: 'athena', method: 'status' });
return view.extend({
	load: function() { return callStatus(); },
	render: function(s) {
		if (!s.daed_running)
			return E([], [ E('h2', {}, _('DAED 面板')), E('div', { class: 'alert-message warning' },
				_('DAED 默认处于安全关闭状态。导入节点和模板后再启动。恢复入口：http://192.168.50.1:8080/')) ]);
		return E('iframe', {
			src: '/athena-daed/',
			style: 'width:100%;height:78vh;border:0;border-radius:8px',
			sandbox: 'allow-same-origin allow-scripts allow-forms allow-downloads allow-popups',
			referrerpolicy: 'same-origin',
			title: 'DAED'
		});
	},
	handleSaveApply: null, handleSave: null, handleReset: null
});
