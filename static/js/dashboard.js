/**
 * Dashboard functionality for HermesQuantum AI
 */

// Inisialisasi chart performa trading
function initPerformanceChart(wins, losses, draws) {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    
    const performanceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Win', 'Loss', 'Draw'],
            datasets: [{
                data: [wins, losses, draws],
                backgroundColor: [
                    '#38b2ac',  // Warna untuk Win
                    '#fc8181',  // Warna untuk Loss
                    '#d6bc00'   // Warna untuk Draw
                ],
                borderColor: [
                    '#2d3748',
                    '#2d3748',
                    '#2d3748'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#a0aec0',
                        font: {
                            size: 12
                        },
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: '#4a5568',
                    titleColor: '#e2e8f0',
                    bodyColor: '#e2e8f0',
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const value = context.raw;
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            return `${context.label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '70%'
        }
    });
}

// Inisialisasi chart aktivitas sinyal
function initSignalActivityChart(signalCounts) {
    const ctx = document.getElementById('signalActivityChart').getContext('2d');
    
    // Buat array untuk 7 hari terakhir
    const days = [];
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        days.push(date.toLocaleDateString('id-ID', { weekday: 'short' }));
    }
    
    const signalActivityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: days,
            datasets: [{
                label: 'Jumlah Sinyal',
                data: signalCounts,
                backgroundColor: 'rgba(56, 178, 172, 0.2)',
                borderColor: '#38b2ac',
                borderWidth: 3,
                pointBackgroundColor: '#38b2ac',
                pointBorderColor: '#2d3748',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#4a5568',
                    titleColor: '#e2e8f0',
                    bodyColor: '#e2e8f0',
                    padding: 10,
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            return `Jumlah Sinyal: ${context.raw}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: '#a0aec0',
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(74, 85, 104, 0.2)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#a0aec0',
                        font: {
                            size: 10
                        },
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// Fetch dan update sinyal terbaru
function fetchLatestSignals() {
    // Tambahkan loader
    const tableBody = document.getElementById('signalsTableBody');
    tableBody.innerHTML = `
        <tr>
            <td colspan="6" style="text-align: center; padding: 30px;">
                <div class="loader"></div>
                <p>Mengambil data sinyal terbaru...</p>
            </td>
        </tr>
    `;
    
    // Fetch sinyal terbaru dari API
    fetch('/api/signals/latest')
        .then(response => response.json())
        .then(signals => {
            if (signals.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" style="text-align: center; padding: 30px;">
                            <i class="fas fa-inbox fa-2x mb-3" style="color: #4a5568;"></i>
                            <p>Belum ada sinyal yang dihasilkan</p>
                        </td>
                    </tr>
                `;
                return;
            }
            
            // Perbarui tabel
            tableBody.innerHTML = '';
            
            signals.forEach(signal => {
                let resultClass = 'pending';
                let resultIcon = 'clock';
                let resultText = 'PENDING';
                
                if (signal.result === 'WIN') {
                    resultClass = 'win';
                    resultIcon = 'check-circle';
                    resultText = 'WIN';
                } else if (signal.result === 'LOSS') {
                    resultClass = 'loss';
                    resultIcon = 'times-circle';
                    resultText = 'LOSS';
                } else if (signal.result === 'DRAW') {
                    resultClass = 'draw';
                    resultIcon = 'minus-circle';
                    resultText = 'DRAW';
                }
                
                const directionClass = signal.direction === 'BUY' ? 'buy' : 'sell';
                const directionIcon = signal.direction === 'BUY' ? 'arrow-up' : 'arrow-down';
                
                const executedTime = new Date(signal.executed_at).toLocaleTimeString();
                
                tableBody.innerHTML += `
                    <tr>
                        <td>${executedTime}</td>
                        <td>${signal.symbol}</td>
                        <td class="signal-direction ${directionClass}">
                            ${signal.direction}
                            <i class="fas fa-${directionIcon} ms-1"></i>
                        </td>
                        <td class="hide-on-mobile">
                            <div class="signal-confidence">
                                <div class="signal-confidence-bar" style="width: ${signal.confidence}%"></div>
                            </div>
                            <small>${signal.confidence}%</small>
                        </td>
                        <td>
                            <span class="signal-result ${resultClass}">
                                <i class="fas fa-${resultIcon} me-1"></i> ${resultText}
                            </span>
                        </td>
                        <td>
                            <a href="/signal/${signal.id}" class="signal-detail-link">
                                <i class="fas fa-external-link-alt me-1"></i> Detail
                            </a>
                        </td>
                    </tr>
                `;
            });
            
            // Perbarui statistik
            updateStatistics(signals);
        })
        .catch(error => {
            console.error('Error fetching signals:', error);
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 30px;">
                        <i class="fas fa-exclamation-triangle fa-2x mb-3" style="color: #fc8181;"></i>
                        <p>Gagal mengambil data. Silakan coba lagi.</p>
                    </td>
                </tr>
            `;
        });
}

// Update statistik dashboard
function updateStatistics(signals) {
    // Hitung jumlah win, loss, dan draw
    let wins = 0;
    let losses = 0;
    let draws = 0;
    
    signals.forEach(signal => {
        if (signal.result === 'WIN') wins++;
        else if (signal.result === 'LOSS') losses++;
        else if (signal.result === 'DRAW') draws++;
    });
    
    // Hitung win rate
    const total = wins + losses + draws;
    const winRate = total > 0 ? Math.round((wins / total) * 100) : 0;
    
    // Update win rate di dashboard
    document.getElementById('win-rate').textContent = `${winRate}%`;
    
    // Update signal count di dashboard
    document.getElementById('signal-count').textContent = `${total}`;
    
    // Perbarui chart
    if (window.performanceChart) {
        window.performanceChart.data.datasets[0].data = [wins, losses, draws];
        window.performanceChart.update();
    } else {
        initPerformanceChart(wins, losses, draws);
    }
}

// Event listener saat halaman dimuat
document.addEventListener('DOMContentLoaded', function() {
    // Set interval untuk memperbarui waktu
    setInterval(function() {
        const now = new Date();
        document.querySelector('.date').textContent = now.toLocaleDateString('id-ID', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }, 60000); // Update setiap menit
});
