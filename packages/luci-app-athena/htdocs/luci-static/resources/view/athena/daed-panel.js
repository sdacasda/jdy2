'use strict';
'require view';
'require rpc';
'require ui';

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

	handleRecoveryCommand: function() {
		ui.showModal(_('DAED recovery via SSH'), [
			E('p', {}, _('Run this command through an interactive SSH terminal. The browser never receives or displays the temporary credential.')),
			E('code', {}, 'athena-daed-reset-password'),
			E('div', { class: 'right' }, [
				E('button', { class: 'btn cbi-button-neutral', click: ui.hideModal }, _('Close'))
			])
		]);
	},

	render: function(s) {
		var backendRunning = !!s.daed_running;
		if (!backendRunning) {
			return E('div', { class: 'athena-daed-card' }, [
				E('h3', {}, _('后端未连接'))
			]);
		}
		var apiReachable = !!s.daed_api_reachable;
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

		page.appendChild(E('div', { class: 'athena-daed-actions' }, [
			s.daed_running
				? E('button', { class: 'btn cbi-button-negative', click: this.handleStop.bind(this) }, _('停止 DAED'))
				: E('button', { class: 'btn cbi-button-positive important', click: this.handleStart.bind(this) }, _('启动 DAED')),
			E('button', { class: 'btn cbi-button-neutral', click: this.handleRefresh.bind(this) }, _('重新检测'))
		]));

		if (backendRunning && !apiReachable) {
				page.appendChild(E('div', {
					class: 'athena-daed-card athena-daed-api-warning',
					role: 'alert'
				}, [
					E('h3', {}, _('DAED database or API is unavailable')),
					E('p', {}, _('Use an interactive SSH terminal to run the recovery command. The browser never receives credentials.')),
					E('button', {
						class: 'btn cbi-button-neutral',
						click: this.handleRecoveryCommand.bind(this)
					}, _('Show SSH recovery command'))
				]));
		}
		page.appendChild(E('iframe', {
				src: '/athena-daed/',
				class: 'athena-daed-frame',
				sandbox: 'allow-same-origin allow-scripts allow-forms allow-modals allow-downloads allow-popups',
				allow: 'clipboard-read; clipboard-write',
				referrerpolicy: 'same-origin',
				title: 'DAED'
		}));
		return page;
	},

	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
