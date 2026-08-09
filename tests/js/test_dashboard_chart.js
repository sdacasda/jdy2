'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const sourcePath = path.join(
  process.cwd(),
  'packages/luci-app-athena/htdocs/luci-static/resources/athena/chart.js'
);
const source = fs.readFileSync(sourcePath, 'utf8');

class LuCIClass {}

LuCIClass.extend = function(members) {
  class Derived extends LuCIClass {}
  Object.assign(Derived.prototype, members);
  return Derived;
};

const ChartClass = Function('L', source)({ Class: LuCIClass });
assert.strictEqual(typeof ChartClass, 'function');
assert.ok(ChartClass.prototype instanceof LuCIClass);

const chart = new ChartClass();
for (const method of [
  'appendSample',
  'deltaRate',
  'cpuPercent',
  'normalizeSeries',
  'polylineSegments'
])
  assert.strictEqual(typeof chart[method], 'function');

let history = chart.appendSample([], { value: 1 }, 200);
assert.deepStrictEqual(history, [{ value: 1 }]);

for (let i = 2; i <= 205; i++)
  history = chart.appendSample(history, { value: i }, 200);
assert.strictEqual(history.length, 200);
assert.strictEqual(history[0].value, 6);
assert.strictEqual(history[199].value, 205);

assert.strictEqual(chart.deltaRate(null, 4000, 3), null);
assert.strictEqual(chart.deltaRate(1000, 4000, 3), 1000);
assert.strictEqual(chart.deltaRate(4000, 1000, 3), 0);
assert.strictEqual(chart.deltaRate(1000, 4000, 0), null);
assert.strictEqual(chart.deltaRate('bad', 4000, 3), null);

assert.strictEqual(chart.cpuPercent(null, null, 100, 50), null);
assert.strictEqual(chart.cpuPercent(100, 50, 200, 80), 70);
assert.strictEqual(chart.cpuPercent(200, 80, 100, 50), 0);
assert.strictEqual(chart.cpuPercent(100, 50, 100, 50), 0);
assert.strictEqual(chart.cpuPercent(0, 100, 100, 100), 100);

const flat = chart.normalizeSeries([42, 42, 42]);
assert.strictEqual(flat.length, 3);
assert.ok(flat.every((value) => value === 0.5));

const segments = chart.polylineSegments([10, null, 20, 30], 100, 40);
assert.strictEqual(segments.length, 2);
assert.ok(segments[0].startsWith('M'));
assert.ok(segments[1].startsWith('M'));
assert.ok(!segments.join(' ').includes('NaN'));
assert.ok(!segments.join(' ').includes('Infinity'));

const unavailable = chart.polylineSegments([null, undefined], 100, 40);
assert.deepStrictEqual(unavailable, []);

console.log('PASS: dashboard chart math');
