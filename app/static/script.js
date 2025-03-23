document.addEventListener("DOMContentLoaded", function() {
  // 1) Chart for Day-of-week distribution
  const dowLabels = ['الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت'];
  // dowData جاي من الـ window:  window.dowData
  const dowData = window.dowData || [0,0,0,0,0,0,0];

  const ctxDOW = document.getElementById('dayOfWeekChart').getContext('2d');
  new Chart(ctxDOW, {
    type: 'bar',
    data: {
      labels: dowLabels,
      datasets: [{
        label: 'عدد الحلاقات',
        data: dowData,
        backgroundColor: 'rgba(52, 152, 219, 0.7)'
      }]
    },
    options: {
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });

  // 2) Trend chart for monthly new clients
  const labelsTrend = window.labelsTrend || [];
  const dataTrend   = window.dataTrend   || [];

  const ctxTrend = document.getElementById('newClientsChart').getContext('2d');
  new Chart(ctxTrend, {
    type: 'line',
    data: {
      labels: labelsTrend,
      datasets: [{
        label: 'عملاء جدد شهريًا',
        data: dataTrend,
        borderColor: 'rgba(46, 204, 113, 1)',
        backgroundColor: 'rgba(46, 204, 113, 0.2)',
        fill: true,
        tension: 0.2
      }]
    },
    options: {
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
});
