'use strict';
'require view';
'require rpc';
'require ui';
var callBackups = rpc.declare({ object: 'athena', method: 'backups' });
var callRollback = rpc.declare({ object: 'athena', method: 'rollback', params: [ 'id', 'confirm' ] });
return view.extend({
	load: function() { return callBackups(); },
	render: function(data) {
		return E([], [ E('h2', {}, _('备份与回滚')), E('pre', {}, data.ids || _('暂无备份')),
			E('p', {}, _('回滚会先校验备份；请通过 SSH 运行 athena-rollback，或在确认对话中提交备份编号。')) ]);
	},
	handleSaveApply: null, handleSave: null, handleReset: null
});
