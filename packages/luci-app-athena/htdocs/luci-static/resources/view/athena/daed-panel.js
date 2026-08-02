'use strict';
'require view';
'require rpc';

var callStatus = rpc.declare({ object: 'athena', method: 'status' });
var callDaedStart = rpc.declare({ object: 'athena', method: 'daed_start' });
var callDaedStop = rpc.declare({ object: 'athena', method: 'daed_stop' });

function statusChip(label, active) {
	return E('div', { class: 'athena-daed-chip ' + (active ? 'is-ok' : 'is-off') }, [
		E('span', { class: 'athena-daed-dot' }),
		E('span', {}, label),
		E('strong', {}, active ? _('正常') : _('未就绪'))
	]);
}

function errorMessage(errorClass) {
	var messages = {
		ebpf: _('DAED 的 eBPF 程序与当前内核不兼容。管理页面仍可使用，请先查看健康检查。'),
		configuration: _('DAED 配置无法加载，请检查最近导入的配置模板。'),
		memory: _('DAED 启动时可用内存不足。'),
		unavailable: _('DAED 管理 API 尚未就绪。'),
		none: _('DAED 尚未启动。')
	};
	return messages[errorClass] || messages.unavailable;
}

return view.extend({
	load: function() {
		return callStatus();
	},

	handleStart: function() {
		return callDaedStart().then(function() { window.location.reload(); });
	},

	handleStop: function() {
		if (!window.confirm(_('确认停止 DAED？代理流量会暂时恢复为普通网络。')))
			return Promise.resolve();
		return callDaedStop().then(function() { window.location.reload(); });
	},

	handleRefresh: function() {
		window.location.reload();
	},

	render: function(s) {
		var ready = s.daed_running && s.daed_api_reachable;
		var page = E('div', { class: 'athena-daed-page' }, [
			E('style', {}, [
				'.athena-daed-page{display:grid;gap:16px}',
				'.athena-daed-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}',
				'.athena-daed-chip{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:16px;border-radius:14px;background:var(--background-color-high,#24262b);border:1px solid rgba(255,255,255,.08)}',
				'.athena-daed-dot{width:10px;height:10px;border-radius:50%;background:#f59e0b}.athena-daed-chip.is-ok .athena-daed-dot{background:#22c55e}',
				'.athena-daed-card{padding:18px;border-radius:14px;background:var(--background-color-high,#24262b);border:1px solid rgba(255,255,255,.08)}',
				'.athena-daed-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}',
				'.athena-daed-frame{width:100%;height:78vh;border:0;border-radius:14px;background:#111}',
				'@media(max-width:700px){.athena-daed-summary{grid-template-columns:1fr}}'
			]),
			E('h2', {}, _('DAED 面板')),
			E('div', { class: 'athena-daed-summary' }, [
				statusChip(_('开机启用'), !!s.daed_enabled),
				statusChip(_('进程运行'), !!s.daed_running),
				statusChip(_('API 可达'), !!s.daed_api_reachable)
			])
		]);

		if (ready) {
			page.appendChild(E('div', { class: 'athena-daed-actions' }, [
				E('button', { class: 'btn cbi-button-negative', click: this.handleStop.bind(this) }, _('停止 DAED')),
				E('button', { class: 'btn cbi-button-neutral', click: this.handleRefresh.bind(this) }, _('重新检测'))
			]));
			page.appendChild(E('iframe', {
				src: '/athena-daed/',
				class: 'athena-daed-frame',
				sandbox: 'allow-same-origin allow-scripts allow-forms allow-downloads allow-popups',
				referrerpolicy: 'same-origin',
				title: 'DAED'
			}));
		} else {
			page.appendChild(E('div', { class: 'athena-daed-card' }, [
				E('h3', {}, _('DAED 尚未就绪')),
				E('p', {}, errorMessage(s.daed_error_class)),
				E('p', {}, [ _('恢复入口：'), E('a', { href: s.recovery_url || '#', target: '_blank', rel: 'noreferrer' }, s.recovery_url || '-') ]),
				E('code', {}, 'athena-health --verbose'),
				E('div', { class: 'athena-daed-actions' }, [
					E('button', { class: 'btn cbi-button-positive important', click: this.handleStart.bind(this) }, s.daed_running ? _('重新启动') : _('启动 DAED')),
					E('button', { class: 'btn cbi-button-neutral', click: this.handleRefresh.bind(this) }, _('重新检测'))
				])
			]));
		}
		return page;
	},

	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
