// let countryData;

// // Load and display list of uploaded country-wise files (readonly, no delete)
// async function loadCountryFiles() {
//   const res = await fetch('/api/countrywise_files');
//   const files = await res.json();
//   const ul = document.getElementById('country-files-list');
//   ul.innerHTML = '';
//   if (files.length === 0) {
//     ul.innerHTML = '<li class="list-group-item text-muted">No country-wise files uploaded yet.</li>';
//     return;
//   }
//   files.forEach(f => {
//     ul.innerHTML += `<li class="list-group-item">${f}</li>`;
//   });
// }

// // --- FILTERS AND CHART ---
// async function initCountryFilters() {
//   const res = await fetch('/api/country_summary');
//   countryData = await res.json();

//   // Extract years from available data
//   const wide = countryData.monthly_by_country || {};
//   const allYM = new Set();

//   if (Object.keys(wide).length) {
//     Object.values(wide).forEach(mmap => Object.keys(mmap).forEach(ym => allYM.add(ym)));
//   }

//   const years = Array.from(allYM)
//     .map(ym => ym.slice(0, 4))
//     .filter((v, i, a) => a.indexOf(v) === i)
//     .sort();

//   const ysel = document.getElementById('country-year');
//   ysel.innerHTML = '';
//   years.forEach(y => ysel.add(new Option(y, y)));
//   document.getElementById('country-filter-btn').disabled = false;
//   renderCountryView();
// }

// document.getElementById('country-filter-btn').addEventListener('click', renderCountryView);

// const MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

// function renderCountryView() {
//   const y = document.getElementById('country-year').value;
//   const m = document.getElementById('country-month').value;
//   const sums = {}, months = new Set();

//   if (countryData.monthly_by_country && Object.keys(countryData.monthly_by_country).length) {
//     for (const [c, mmap] of Object.entries(countryData.monthly_by_country)) {
//       sums[c] = {};
//       for (const [ym, cnt] of Object.entries(mmap)) {
//         if ((!y || ym.startsWith(y)) && (!m || ym.slice(5) === m)) {
//           sums[c][ym] = cnt;
//           months.add(ym);
//         }
//       }
//     }
//   }

//   const monthKeys = Array.from(months).sort();
//   const avg = {};
//   Object.entries(sums).forEach(([c, map]) => {
//     const vals = Object.values(map);
//     avg[c] = vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2) : '0.00';
//   });
//   const countries = Object.keys(sums).sort();
//   const cont = document.getElementById('country-charts');
//   if (!countries.length) {
//     cont.innerHTML = '<p class="text-muted">No country data available.</p>';
//     return;
//   }
//   const hdr = [
//     '<th>Country</th>',
//     `<th>Avg of ${monthKeys.length} mo [${y}]</th>`
//   ].concat(monthKeys.map(ym => {
//     const [yr, mo] = ym.split('-');
//     return `<th>${MONTH_ABBR[+mo - 1]}-${yr.slice(2)}</th>`;
//   })).join('');
//   const rows = countries.map(c => {
//     const cells = [
//       `<td>${c}</td>`,
//       `<td>${avg[c]}</td>`
//     ].concat(monthKeys.map(ym => `<td>${sums[c][ym] || 0}</td>`)).join('');
//     return `<tr>${cells}</tr>`;
//   }).join('');
//   cont.innerHTML = `
//     <div class="mb-4">
//       <canvas id="country-chart"
//               style="width:100%;max-width:900px;height:300px"></canvas>
//     </div>
//     <div class="table-responsive">
//       <table class="table table-dark table-striped">
//         <thead><tr>${hdr}</tr></thead>
//         <tbody>${rows}</tbody>
//       </table>
//     </div>
//   `;
//   const ctx = document.getElementById('country-chart').getContext('2d');
//   if (window.countryChart) window.countryChart.destroy();
//   window.countryChart = new Chart(ctx, {
//     type: 'bar',
//     data: {
//       labels: countries,
//       datasets: [{
//         label: 'Transactions',
//         data: countries.map(c =>
//           Object.values(sums[c]).reduce((a, b) => a + b, 0)
//         ),
//         backgroundColor: 'rgba(0,65,130,0.7)'
//       }]
//     },
//     options: { scales: { y: { beginAtZero: true } } }
//   });
// }

// // Initial boot
// document.getElementById('country-filter-btn').disabled = true;
// window.addEventListener('DOMContentLoaded', async () => {
//   await loadCountryFiles();
//   await initCountryFilters();
// });
