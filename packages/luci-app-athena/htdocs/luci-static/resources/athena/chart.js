'use strict';

function finiteNumber(value) {
	if (value === null || value === undefined || value === '')
		return null;
	var number = Number(value);
	return Number.isFinite(number) ? number : null;
}

function appendSample(series, point, limit) {
	var output = Array.isArray(series) ? series.slice() : [];
	var maximum = Math.max(1, Number(limit) || 1);

	output.push(point);
	if (output.length > maximum)
		output.splice(0, output.length - maximum);

	return output;
}

function deltaRate(previous, current, elapsedSeconds) {
	var before = finiteNumber(previous);
	var after = finiteNumber(current);
	var elapsed = finiteNumber(elapsedSeconds);

	if (before === null || after === null || elapsed === null || elapsed <= 0)
		return null;
	if (after < before)
		return 0;

	return (after - before) / elapsed;
}

function cpuPercent(previousTotal, previousIdle, currentTotal, currentIdle) {
	var beforeTotal = finiteNumber(previousTotal);
	var beforeIdle = finiteNumber(previousIdle);
	var afterTotal = finiteNumber(currentTotal);
	var afterIdle = finiteNumber(currentIdle);

	if (beforeTotal === null || beforeIdle === null ||
	    afterTotal === null || afterIdle === null)
		return null;
	if (afterTotal < beforeTotal || afterIdle < beforeIdle)
		return 0;

	var totalDelta = afterTotal - beforeTotal;
	var idleDelta = afterIdle - beforeIdle;
	if (totalDelta <= 0)
		return 0;

	var percentage = (1 - idleDelta / totalDelta) * 100;
	return Math.max(0, Math.min(100, percentage));
}

function normalizeSeries(values) {
	var source = Array.isArray(values) ? values : [];
	var numeric = source
		.map(finiteNumber)
		.filter(function(value) { return value !== null; });

	if (!numeric.length)
		return source.map(function() { return null; });

	var minimum = Math.min.apply(null, numeric);
	var maximum = Math.max.apply(null, numeric);
	if (minimum === maximum) {
		return source.map(function(value) {
			return finiteNumber(value) === null ? null : 0.5;
		});
	}

	return source.map(function(value) {
		var number = finiteNumber(value);
		return number === null ? null : (number - minimum) / (maximum - minimum);
	});
}

function polylineSegments(values, width, height) {
	var source = Array.isArray(values) ? values : [];
	var normalized = normalizeSeries(source);
	var chartWidth = Math.max(1, finiteNumber(width) || 1);
	var chartHeight = Math.max(1, finiteNumber(height) || 1);
	var divisor = Math.max(1, source.length - 1);
	var segments = [];
	var current = [];

	function flush() {
		if (current.length) {
			segments.push(current.join(' '));
			current = [];
		}
	}

	normalized.forEach(function(value, index) {
		if (value === null) {
			flush();
			return;
		}

		var x = Math.round(index / divisor * chartWidth * 100) / 100;
		var y = Math.round((chartHeight - value * chartHeight) * 100) / 100;
		current.push((current.length ? 'L' : 'M') + x + ' ' + y);
	});
	flush();

	return segments;
}

return Object.freeze({
	appendSample: appendSample,
	deltaRate: deltaRate,
	cpuPercent: cpuPercent,
	normalizeSeries: normalizeSeries,
	polylineSegments: polylineSegments
});
