// ========== GLOBAL VARS ==========
let fullData, cvData;

// ========== FILTER INIT ==========
async function initFilters() {
  const res = await fetch('/api/summary');
  fullData = await res.json();

  // Populate year selects
  const allDates = Object.keys(fullData.daily_counts || {});
  const years = [...new Set(allDates.map(d => d.slice(0, 4)))].sort();
  const ysel = document.getElementById('year-select');
  const cysel = document.getElementById('compare-year-select');
  ysel.innerHTML = '';
  cysel.innerHTML = '';
  years.forEach(y => {
    ysel.add(new Option(y, y));
    cysel.add(new Option(y, y));
  });
  // Set default selected to latest year if present
  if (years.length) {
    ysel.value = years[years.length-1];
    cysel.value = years[years.length-2] || years[years.length-1];
  }
}

// ========== UTILITIES ==========
function formatAmount(n) {
  return n?.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}) || '0.00';
}
function pickDates(y, m) {
  if (!fullData.daily_counts) return [];
  return Object.keys(fullData.daily_counts)
    .filter(d => (!y || d.startsWith(y)) && (!m || d.slice(5,7) === m));
}
function sumOver(dates, map) {
  if (!map) return 0;
  return dates.reduce((s,d) => s + (map[d] || 0), 0);
}
const BANK_ALIASES = { "CARGILLS": "CARGILLS", "Carg": "CARGILLS" /* etc */ };
function buildBankBreakdown(dates) {
  const out = {};
  for (const [rawBank, dateMap] of Object.entries(fullData.bank_counts || {})) {
    const std = BANK_ALIASES[rawBank] || rawBank;
    const cnt = sumOver(dates, dateMap);
    out[std] = (out[std] || 0) + cnt;
  }
  return out;
}
function buildCountryBreakdown(dates) {
  if (!fullData.senders_country_by_date) return {};
  const out = {};
  for (const [date, countryCounts] of Object.entries(fullData.senders_country_by_date)) {
    if (!dates.includes(date)) continue;
    for (const [country, cnt] of Object.entries(countryCounts)) {
      out[country] = (out[country] || 0) + cnt;
    }
  }
  return out;
}
function buildStatusBreakdown(dates) {
  if (!fullData.transaction_status_by_date) return {};
  const out = {};
  for (const [date, statusCounts] of Object.entries(fullData.transaction_status_by_date)) {
    if (!dates.includes(date)) continue;
    for (const [status, cnt] of Object.entries(statusCounts)) {
      out[status] = (out[status] || 0) + cnt;
    }
  }
  return out;
}
function populateList(ulId, data) {
  const ul = document.getElementById(ulId);
  ul.innerHTML = '';
  for (const [k, v] of Object.entries(data)) {
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between';
    li.innerHTML = `<span>${k}</span><span>${v}</span>`;
    ul.appendChild(li);
  }
}

// ========== CHARTS ==========
function drawComparisonChart(bd, cd) {
  const ctx = document.getElementById('comparison-chart').getContext('2d');
  if (window.dailyChart) window.dailyChart.destroy();
  const labels = [...new Set([...Object.keys(bd), ...Object.keys(cd)])].sort();
  const bVals = labels.map(l => bd[l] || 0);
  const cVals = labels.map(l => cd[l] || 0);
  window.dailyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Base',    data: bVals, backgroundColor: 'rgba(0,65,130,0.7)' },
        { label: 'Compare', data: cVals, backgroundColor: 'rgba(0,161,228,0.7)' }
      ]
    },
    options: { scales: { y: { beginAtZero: true } } }
  });
}
function drawYearlyChart(year1Data, year2Data, label1, label2) {
  const ctx = document.getElementById('yearly-chart').getContext('2d');
  if (window.yearChart) window.yearChart.destroy();
  const months = ['01','02','03','04','05','06','07','08','09','10','11','12'];
  const y1 = months.map(m => year1Data[m] || 0);
  const y2 = months.map(m => year2Data[m] || 0);
  window.yearChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: months,
      datasets: [
        { label: label1, data: y1, tension: 0.3, borderColor: 'rgba(0,65,130,0.8)', fill: false },
        { label: label2, data: y2, tension: 0.3, borderColor: 'rgba(0,161,228,0.8)', fill: false }
      ]
    },
    options: { scales: { y: { beginAtZero: true } } }
  });
}

// ========== FORECAST ==========
async function drawForecast(year, month) {
  const params = new URLSearchParams({ year, month });
  const res    = await fetch('/api/forecast?' + params.toString());
  const data   = await res.json();

  const labels = Object.keys(data);
  const values = Object.values(data);

  const title = month
    ? `${year}-${month} Forecast`
    : `${year} Forecast (Monthly)`;
  document.getElementById('forecast-title').textContent = title;

  const ctx = document.getElementById('forecast-chart').getContext('2d');
  if (window.forecastChart) window.forecastChart.destroy();
  window.forecastChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Forecast',
        data: values,
        borderColor: 'rgba(255,193,7,0.8)',
        pointBackgroundColor: 'rgba(255,193,7,0.8)',
        tension: 0.3,
        fill: false
      }]
    },
    options: {
      scales: { y: { beginAtZero: true } },
      plugins:{ legend:{ labels:{ color:'#ff0' } } }
    }
  });
}

// ========== REPRESENTATIVE SUMMARY ==========
function populateRepTable(cnts, visits) {
  const tb = document.querySelector('#rep-table tbody');
  tb.innerHTML = '';
  for (const [rep, cnt] of Object.entries(cnts || {})) {
    const v = visits[rep] || {};
    tb.insertAdjacentHTML('beforeend', `
      <tr>
        <td>${rep}</td>
        <td>${cnt}</td>
        <td>${v.first || ''}</td>
        <td>${v.last  || ''}</td>
      </tr>`);
  }
}

// ========== COUNTRY-WISE ANALYSIS ==========
async function loadCountryData() {
  cvData = await fetch('/api/country_summary').then(r=>r.json());
  renderCountryView();
}
const MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function renderCountryView(){
  if (!cvData) return;
  const y = document.getElementById('year-select').value;
  const m = document.getElementById('month-select').value;

  // build per-country monthly sums
  const monthly = {}, months = new Set();
  if (cvData.monthly_by_country && Object.keys(cvData.monthly_by_country).length) {
    for (const [c,map] of Object.entries(cvData.monthly_by_country)) {
      monthly[c] = {};
      for (const [ym,cnt] of Object.entries(map)) {
        if ((!y||ym.startsWith(y)) && (!m||ym.slice(5)===m)) {
          monthly[c][ym] = cnt;
          months.add(ym);
        }
      }
    }
  } else {
    for (const [c,map] of Object.entries(cvData.daily_by_country||{})) {
      monthly[c] = {};
      for (const [d,cnt] of Object.entries(map)) {
        if (!d.startsWith(y)) continue;
        const ym = d.slice(0,7);
        if (m && ym.slice(5)!==m) continue;
        monthly[c][ym] = (monthly[c][ym]||0) + cnt;
        months.add(ym);
      }
    }
  }
  const keys = Array.from(months).sort();
  const avg  = {};
  for (const c of Object.keys(monthly)) {
    const vals = Object.values(monthly[c]);
    avg[c] = vals.length
      ? (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(2)
      : '0.00';
  }
  const countries = Object.keys(monthly).sort();
  const cont      = document.getElementById('cv-container');
  if (!countries.length) {
    cont.innerHTML = '<p class="text-muted">No country data available.</p>';
    return;
  }
  // table header
  const hdr = [
    '<th>Country</th>',
    `<th>Avg of ${keys.length} mo [${y}]</th>`
  ].concat(
    keys.map(ym=>{
      const [yr,mo] = ym.split('-');
      return `<th>${MONTH_ABBR[+mo-1]}-${yr.slice(2)}</th>`;
    })
  ).join('');
  // rows
  const rows = countries.map(c=>{
    const cells = [
      `<td>${c}</td>`,
      `<td>${avg[c]}</td>`
    ].concat(
      keys.map(k=>`<td>${monthly[c][k]||0}</td>`)
    ).join('');
    return `<tr>${cells}</tr>`;
  }).join('');
  // render chart + table
  cont.innerHTML = `
    <div class="mb-4">
      <canvas id="cv-chart"
              style="width:100%;max-width:900px;height:300px"></canvas>
    </div>
    <div class="table-responsive">
      <table class="table table-dark table-striped">
        <thead><tr>${hdr}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  // draw bar chart
  const ctx = document.getElementById('cv-chart').getContext('2d');
  if (window.cvChart) window.cvChart.destroy();
  window.cvChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: countries,
      datasets: [{
        label: 'Transactions',
        data: countries.map(c=>
          Object.values(monthly[c]).reduce((a,b)=>a+b,0)
        ),
        backgroundColor: 'rgba(0,65,130,0.7)'
      }]
    },
    options:{ scales:{ y:{ beginAtZero:true } } }
  });
}

// ========== ON FILTER BUTTON CLICK ==========
document.getElementById('filter-btn').addEventListener('click', () => {
  const y  = document.getElementById('year-select').value;
  const m  = document.getElementById('month-select').value;
  const cy = document.getElementById('compare-year-select').value;
  const cm = document.getElementById('compare-month-select').value;

  // Transactions summary
  const baseDates = pickDates(y, m);
  const compDates = pickDates(cy, cm);
  const baseCnt = sumOver(baseDates, fullData.daily_counts);
  const compCnt = sumOver(compDates, fullData.daily_counts);
  const baseAmt = sumOver(baseDates, fullData.daily_amounts||{});
  const compAmt = sumOver(compDates, fullData.daily_amounts||{});
  document.getElementById('base-count').innerText  = `Count: ${baseCnt}`;
  document.getElementById('base-amount').innerText = `Total Amount: ${formatAmount(baseAmt)}`;
  document.getElementById('comp-count').innerText  = `Count: ${compCnt}`;
  document.getElementById('comp-amount').innerText = `Total Amount: ${formatAmount(compAmt)}`;

  // By Bank
  populateList('base-bank-list', buildBankBreakdown(baseDates));
  populateList('comp-bank-list', buildBankBreakdown(compDates));
  // By Sender's Country
  populateList('base-country-list', buildCountryBreakdown(baseDates));
  populateList('comp-country-list', buildCountryBreakdown(compDates));
  // By Transaction Status
  populateList('base-status-list', buildStatusBreakdown(baseDates));
  populateList('comp-status-list', buildStatusBreakdown(compDates));

  // Charts
  drawComparisonChart(
    Object.fromEntries(baseDates.map(d=>[d,fullData.daily_counts[d]])),
    Object.fromEntries(compDates.map(d=>[d,fullData.daily_counts[d]]))
  );
  // Yearly (monthly aggregate)
  const agg = dates => {
    const s = {};
    dates.forEach(d=>{
      const mo = d.slice(5,7);
      s[mo] = (s[mo]||0) + fullData.daily_counts[d];
    });
    return s;
  };
  drawYearlyChart(agg(baseDates), agg(compDates), y||'Base', cy||'Compare');
  // Rep
  populateRepTable(fullData.rep_counts, fullData.visit_info);
  // Country view
  renderCountryView();
});

// ========== FORECAST BUTTON ==========
const predictBtn     = document.getElementById('predict-btn');
const predictText    = document.getElementById('predict-text');
const predictSpinner = document.getElementById('predict-spinner');
predictBtn.addEventListener('click', async () => {
  const year  = document.getElementById('forecast-year').value;
  const month = document.getElementById('forecast-month').value;
  predictSpinner.classList.remove('d-none');
  predictBtn.disabled = true;
  predictText.textContent = 'Predicting…';
  try {
    await drawForecast(year, month);
  } catch(err) {
    console.error(err);
    alert('Forecast failed.');
  } finally {
    predictSpinner.classList.add('d-none');
    predictBtn.disabled = false;
    predictText.textContent = 'Predict';
  }
});

// ========== INITIAL LOAD ==========
window.addEventListener('DOMContentLoaded', async () => {
  await initFilters();
  document.getElementById('filter-btn').click();
  await loadCountryData();
  predictBtn.disabled = false;
  drawForecast(
    document.getElementById('forecast-year').value,
    document.getElementById('forecast-month').value
  );
});
