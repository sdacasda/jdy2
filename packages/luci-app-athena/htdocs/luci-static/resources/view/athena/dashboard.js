'use strict';
'require view';
'require rpc';
'require poll';
'require dom';
'require athena.chart as chart';

var POLL_SECONDS = 3;
var MAX_POINTS = 200;
var TEMP_WARNING = 80;
var TEMP_CRITICAL = 90;

var callDashboard = rpc.declare({
	object: 'athena',
	method: 'dashboard',
	expect: {}
});

function available(value) {
	return value !== null && value !== undefined && value !== '';
}

function formatPercent(value) {
	return available(value) && Number.isFinite(Number(value))
		? Number(value).toFixed(1) + '%'
		: '—';
}

function formatRate(value) {
	if (!available(value) || !Number.isFinite(Number(value)))
		return '—';
	var units = [ 'B/s', 'KiB/s', 'MiB/s', 'GiB/s' ];
	var number = Math.max(0, Number(value));
	var unit = 0;
	while (number >= 1024 && unit < units.length - 1) {
		number /= 1024;
		unit++;
	}
	return number.toFixed(unit ? 1 : 0) + ' ' + units[unit];
}

function formatTemperature(value) {
	return available(value) && Number.isFinite(Number(value))
		? Number(value).toFixed(1) + ' °C'
		: '暂不可用';
}

function formatUptime(value) {
	if (!available(value) || !Number.isFinite(Number(value)))
		return '暂不可用';
	var seconds = Math.max(0, Math.floor(Number(value)));
	var days = Math.floor(seconds / 86400);
	var hours = Math.floor(seconds % 86400 / 3600);
	var minutes = Math.floor(seconds % 3600 / 60);
	return (days ? days + ' 天 ' : '') + hours + ' 小时 ' + minutes + ' 分';
}

function boolText(value, yes, no) {
	return value === true ? yes : value === false ? no : '暂不可用';
}

function detailRow(label, value) {
	return E('div', { class: 'athena-detail-row' }, [
		E('span', {}, label),
		E('span', {}, value)
	]);
}

function statusPill(label, value, severity) {
	var text = label + '：' + value;
	return E('div', {
		class: 'athena-status-pill is-' + severity,
		role: 'status',
		'aria-label': text
	}, [
		E('span', { class: 'athena-status-dot', 'aria-hidden': 'true' }),
		E('span', {}, [
			E('span', { class: 'athena-status-name' }, label),
			E('span', { class: 'athena-status-value' }, value)
		])
	]);
}

function card(label, value, rows, note) {
	return E('section', { class: 'athena-dashboard-card' }, [
		E('div', { class: 'athena-card-label' }, label),
		E('div', { class: 'athena-card-value' }, value),
		E('div', { class: 'athena-card-details' }, rows || []),
		note ? E('div', { class: 'athena-card-note' }, note) : ''
	]);
}

function thermalMap(snapshot) {
	var output = {};
	(snapshot.thermal || []).forEach(function(item, index) {
		if (!item || !available(item.millicelsius))
			return;
		var key = item.id || ('thermal-' + index);
		while (Object.prototype.hasOwnProperty.call(output, key))
			key += '-' + index;
		output[key] = {
			label: item.label || key,
			value: Number(item.millicelsius) / 1000
		};
	});
	return output;
}

function memoryPercent(memory) {
	if (!memory || !available(memory.total_kib) ||
	    !available(memory.available_kib) || Number(memory.total_kib) <= 0)
		return null;
	return Math.max(0, Math.min(100,
		(1 - Number(memory.available_kib) / Number(memory.total_kib)) * 100));
}

function sampleFrom(snapshot, previous) {
	var elapsed = previous && available(previous.sampled_at) &&
		available(snapshot.sampled_at)
		? Number(snapshot.sampled_at) - Number(previous.sampled_at)
		: null;
	var temperatures = thermalMap(snapshot);
	var sample = {
		time: snapshot.sampled_at,
		cpu: previous ? chart.cpuPercent(
			previous.cpu && previous.cpu.total_ticks,
			previous.cpu && previous.cpu.idle_ticks,
			snapshot.cpu && snapshot.cpu.total_ticks,
			snapshot.cpu && snapshot.cpu.idle_ticks
		) : null,
		memory: memoryPercent(snapshot.memory),
		rx: previous ? chart.deltaRate(
			previous.wan && previous.wan.rx_bytes,
			snapshot.wan && snapshot.wan.rx_bytes,
			elapsed
		) : null,
		tx: previous ? chart.deltaRate(
			previous.wan && previous.wan.tx_bytes,
			snapshot.wan && snapshot.wan.tx_bytes,
			elapsed
		) : null,
		temperatures: {}
	};
	Object.keys(temperatures).forEach(function(key) {
		sample.temperatures[key] = temperatures[key].value;
	});
	return sample;
}

function seriesValues(samples, getter) {
	return samples.map(function(sample) {
		var value = getter(sample);
		return available(value) && Number.isFinite(Number(value))
			? Number(value)
			: null;
	});
}

function svgPaths(values, className) {
	var segments = chart.polylineSegments(values, 100, 40);
	return segments.map(function(pathData) {
		return E('path', {
			class: 'athena-chart-path ' + className,
			d: pathData
		});
	});
}

function chartPanel(title, labels, series, ariaLabel) {
	var paths = [];
	series.forEach(function(item, index) {
		paths = paths.concat(svgPaths(item.values,
			index ? 'series-' + [ 'two', 'three', 'four', 'five' ][index - 1] : ''));
	});
	return E('section', { class: 'athena-dashboard-chart' }, [
		E('div', { class: 'athena-chart-header' }, [
			E('div', { class: 'athena-chart-title' }, title),
			E('div', { class: 'athena-chart-legend' }, labels.map(function(item, index) {
				return E('span', { class: 'athena-legend-item' }, [
					E('span', {
						class: 'athena-legend-swatch series-' + index,
						'aria-hidden': 'true'
					}),
					E('span', {}, item)
				]);
			}))
		]),
		paths.length
			? E('svg', {
				class: 'athena-chart-svg',
				viewBox: '0 0 100 40',
				preserveAspectRatio: 'none',
				role: 'img',
				'aria-label': ariaLabel
			}, [
				E('line', { class: 'athena-chart-gridline', x1: 0, y1: 20, x2: 100, y2: 20 })
			].concat(paths))
			: E('div', { class: 'athena-empty', role: 'status' }, '等待第二个采样点')
	]);
}

function alertBox(level, title, detail) {
	return E('div', {
		class: 'athena-alert is-' + level,
		role: 'status',
		'aria-label': title
	}, [
		E('span', { class: 'athena-alert-title' }, title),
		E('span', {}, detail)
	]);
}

function warnings(snapshot) {
	var items = [];
	var wan = snapshot.wan || {};
	var wireless = snapshot.wireless || {};
	var daed = snapshot.daed || {};
	var temperatures = thermalMap(snapshot);

	if (snapshot.system && snapshot.system.password_set === false)
		items.push(alertBox('warning', '管理员密码未设置',
			'请尽快设置管理密码，避免局域网内未授权访问。'));
	if (snapshot.system && snapshot.system.time_synced === false)
		items.push(alertBox('warning', '时间未同步',
			'系统时间仍不可信；请检查 WAN、NTP 和时区设置。'));
	if (daed.error_code === 'ebpf_local_tcp_sockops')
		items.push(alertBox('critical', 'DAED 内核组件不兼容',
			'local_tcp_sockops 无法在当前内核加载。请打开“服务 → Athena 优化 → DAED 面板”查看日志。'));
	else if (daed.error_code === 'ebpf_verifier')
		items.push(alertBox('critical', 'DAED eBPF 校验失败',
			'内核拒绝了 DAED eBPF 程序，请查看 DAED 面板日志。'));
	else if (daed.error_code === 'startup_failure')
		items.push(alertBox('critical', 'DAED 启动失败',
			'DAED 未能完成启动，请查看 DAED 面板日志。'));
	if (wan.up === false)
		items.push(alertBox('critical', 'WAN 已断开', '上行链路当前不可用。'));
	else if (wan.dns_ok === false)
		items.push(alertBox('warning', 'DNS 异常', 'WAN 未提供可用 DNS 配置。'));
	if (available(wireless.radios_total) && available(wireless.radios_up) &&
	    Number(wireless.radios_up) < Number(wireless.radios_total))
		items.push(alertBox('warning', 'Wi-Fi 射频离线',
			'部分无线射频没有处于运行状态。'));
	Object.keys(temperatures).forEach(function(key) {
		var item = temperatures[key];
		if (item.value >= TEMP_CRITICAL)
			items.push(alertBox('critical', item.label + ' 温度过高',
				formatTemperature(item.value)));
		else if (item.value >= TEMP_WARNING)
			items.push(alertBox('warning', item.label + ' 温度较高',
				formatTemperature(item.value)));
	});
	if (daed.installed === true && daed.running === false && !daed.error_code)
		items.push(alertBox('info', 'DAED 处于安全关闭状态',
			'首次启动默认不会自动启用代理。'));

	return items;
}

function statusStrip(snapshot) {
	var wan = snapshot.wan || {};
	var daed = snapshot.daed || {};
	var system = snapshot.system || {};
	return [
		statusPill('互联网', boolText(wan.up && wan.dns_ok, '正常', '异常'),
			wan.up && wan.dns_ok ? 'good' : 'critical'),
		statusPill('DAED',
			daed.running ? '运行中' : daed.installed ? '已关闭' : '未安装',
			daed.running ? 'good' : daed.error_code ? 'critical' : 'warning'),
		statusPill('IPv4', boolText(wan.ipv4, '已连接', '未连接'),
			wan.ipv4 ? 'good' : 'warning'),
		statusPill('IPv6', boolText(wan.ipv6, '已连接', '未连接'),
			wan.ipv6 ? 'good' : 'warning'),
		statusPill('系统时间', boolText(system.time_synced, '已同步', '未同步'),
			system.time_synced ? 'good' : 'warning'),
		statusPill('运行时间', formatUptime(system.uptime_seconds), 'good')
	];
}

function cards(snapshot, latest) {
	var system = snapshot.system || {};
	var memory = snapshot.memory || {};
	var wan = snapshot.wan || {};
	var wireless = snapshot.wireless || {};
	var daed = snapshot.daed || {};
	var acceleration = snapshot.acceleration || {};
	var temperatures = thermalMap(snapshot);
	var temperatureRows = Object.keys(temperatures).map(function(key) {
		return detailRow(temperatures[key].label,
			formatTemperature(temperatures[key].value));
	});

	return [
		card('CPU', formatPercent(latest.cpu), [
			detailRow('1 分钟负载', available(system.load_1) ? String(system.load_1) : '—'),
			detailRow('5 分钟负载', available(system.load_5) ? String(system.load_5) : '—'),
			detailRow('15 分钟负载', available(system.load_15) ? String(system.load_15) : '—')
		]),
		card('内存', formatPercent(latest.memory), [
			detailRow('总量', available(memory.total_kib)
				? (Number(memory.total_kib) / 1024).toFixed(0) + ' MiB' : '—'),
			detailRow('可用', available(memory.available_kib)
				? (Number(memory.available_kib) / 1024).toFixed(0) + ' MiB' : '—')
		]),
		card('温度', temperatureRows.length
			? formatTemperature(temperatures.cpu && temperatures.cpu.value)
			: '暂不可用', temperatureRows),
		card('WAN', formatRate(latest.rx) + ' ↓', [
			detailRow('上行', formatRate(latest.tx)),
			detailRow('链路', boolText(wan.up, '已连接', '已断开')),
			detailRow('设备', wan.device || '—')
		]),
		card('Wi-Fi / IoT', available(wireless.clients_total)
			? wireless.clients_total + ' 台客户端' : '暂不可用', [
			detailRow('射频', available(wireless.radios_up) &&
				available(wireless.radios_total)
				? wireless.radios_up + ' / ' + wireless.radios_total : '—'),
			detailRow('IoT SSID', available(wireless.iot_clients)
				? wireless.iot_clients + ' 台' : '未启用或不可用')
		]),
		card('DAED / NSS', daed.running ? '代理运行中' : '代理未运行', [
			detailRow('NSS', boolText(acceleration.nss_loaded, '已加载', '未加载')),
			detailRow('ECM IPv4', boolText(acceleration.ecm_ipv4_stopped, '已停止', '未停止')),
			detailRow('ECM IPv6', boolText(acceleration.ecm_ipv6_stopped, '已停止', '未停止')),
			detailRow('Flow Offload', acceleration.flow_offload === false &&
				acceleration.flow_offload_hw === false ? '已关闭' : '需要检查')
		], '保留 NSS/Wi-Fi offload；ECM frontend 保持停止。')
	];
}

function charts(samples) {
	var latest = samples.length ? samples[samples.length - 1] : {};
	var temperatureKeys = {};
	samples.forEach(function(sample) {
		Object.keys(sample.temperatures || {}).forEach(function(key) {
			temperatureKeys[key] = true;
		});
	});
	var tempSeries = Object.keys(temperatureKeys).slice(0, 5).map(function(key) {
		return {
			values: seriesValues(samples, function(sample) {
				return sample.temperatures && sample.temperatures[key];
			})
		};
	});

	return [
		chartPanel('WAN 实时速率',
			[ '下行 ' + formatRate(latest.rx), '上行 ' + formatRate(latest.tx) ],
			[
				{ values: seriesValues(samples, function(sample) { return sample.rx; }) },
				{ values: seriesValues(samples, function(sample) { return sample.tx; }) }
			],
			'WAN 下行和上行实时速率曲线'),
		chartPanel('CPU / 内存',
			[ 'CPU ' + formatPercent(latest.cpu), '内存 ' + formatPercent(latest.memory) ],
			[
				{ values: seriesValues(samples, function(sample) { return sample.cpu; }) },
				{ values: seriesValues(samples, function(sample) { return sample.memory; }) }
			],
			'CPU 和内存使用率曲线'),
		chartPanel('温度',
			Object.keys(temperatureKeys).slice(0, 5).map(function(key) {
				return key + ' ' + formatTemperature(
					latest.temperatures && latest.temperatures[key]);
			}),
			tempSeries,
			'CPU NSS 和 Wi-Fi 温度曲线')
	];
}

return view.extend({
	state: null,
	nodes: null,

	load: function() {
		return callDashboard();
	},

	render: function(snapshot) {
		this.state = {
			samples: [],
			previous: null,
			consecutiveFailures: 0,
			lastSuccessAt: null
		};
		this.nodes = {
			status: E('div', { class: 'athena-status-strip' }),
			alerts: E('div', { class: 'athena-alerts' }),
			cards: E('div', { class: 'athena-dashboard-grid' }),
			charts: E('div', { class: 'athena-charts' }),
			lastUpdate: E('div', { class: 'athena-last-update', role: 'status' })
		};

		this.handleSnapshot(snapshot);
		poll.add(L.bind(function() {
			return callDashboard().then(L.bind(function(next) {
				this.handleSnapshot(next);
			}, this)).catch(L.bind(function() {
				this.handleFailure();
			}, this));
		}, this), POLL_SECONDS);

		return E([], [
			E('link', {
				rel: 'stylesheet',
				type: 'text/css',
				href: L.resource('athena/dashboard.css')
			}),
			E('div', { class: 'athena-dashboard' }, [
				E('header', { class: 'athena-dashboard-header' }, [
					E('div', {}, [
						E('h2', { class: 'athena-dashboard-title' }, 'Athena AX6600'),
						E('div', { class: 'athena-dashboard-subtitle' },
							'实时系统、网络、Wi-Fi、DAED 与 NSS 仪表盘')
					]),
					this.nodes.lastUpdate
				]),
				this.nodes.status,
				this.nodes.alerts,
				this.nodes.cards,
				this.nodes.charts
			])
		]);
	},

	handleSnapshot: function(snapshot) {
		if (!snapshot || snapshot.schema_version !== 1) {
			this.handleFailure();
			return;
		}
		var sample = sampleFrom(snapshot, this.state.previous);
		this.state.samples = chart.appendSample(
			this.state.samples, sample, MAX_POINTS);
		this.state.previous = snapshot;
		this.state.consecutiveFailures = 0;
		this.state.lastSuccessAt = new Date();
		this.update(snapshot, sample);
	},

	handleFailure: function() {
		this.state.consecutiveFailures++;
		if (this.state.consecutiveFailures >= 2) {
			var when = this.state.lastSuccessAt
				? this.state.lastSuccessAt.toLocaleTimeString()
				: '尚无成功数据';
			dom.content(this.nodes.alerts, [
				alertBox('critical', '数据已中断',
					'最近成功更新时间：' + when)
			]);
		}
	},

	update: function(snapshot, sample) {
		dom.content(this.nodes.status, statusStrip(snapshot));
		dom.content(this.nodes.alerts, warnings(snapshot));
		dom.content(this.nodes.cards, cards(snapshot, sample));
		dom.content(this.nodes.charts, charts(this.state.samples));
		dom.content(this.nodes.lastUpdate,
			'最近成功更新：' + this.state.lastSuccessAt.toLocaleTimeString() +
			' · 每 3 秒采样 · 最多 200 点');
	},

	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
