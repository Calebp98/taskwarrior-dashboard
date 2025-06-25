#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import sys

def parse_taskwarrior_data():
    """Parse completed and pending tasks from Task Warrior's SQLite database"""
    db_file = os.path.expanduser("~/.task/taskchampion.sqlite3")
    
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found", file=sys.stderr)
        return {}, {}
    
    daily_completed = Counter()
    daily_pending = Counter()
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Query all tasks - data is stored as JSON in the 'data' column
        cursor.execute("SELECT data FROM tasks")
        
        for row in cursor.fetchall():
            try:
                task_json = row[0]
                if task_json:
                    task_data = json.loads(task_json)
                    
                    if task_data.get('status') == 'completed' and 'end' in task_data:
                        # Handle completed tasks
                        end_timestamp = task_data['end']
                        # Handle both Unix timestamp and ISO format
                        if isinstance(end_timestamp, (int, float)):
                            # Unix timestamp as number
                            end_date = datetime.fromtimestamp(end_timestamp)
                        elif end_timestamp.isdigit():
                            # Unix timestamp as string
                            end_date = datetime.fromtimestamp(int(end_timestamp))
                        else:
                            # ISO format like "20241225T143022Z"
                            end_date = datetime.strptime(end_timestamp, "%Y%m%dT%H%M%SZ")
                        date_str = end_date.strftime("%Y-%m-%d")
                        daily_completed[date_str] += 1
                        
                    elif task_data.get('status') == 'pending' and 'entry' in task_data:
                        # Handle pending tasks by entry date
                        entry_timestamp = task_data['entry']
                        if isinstance(entry_timestamp, (int, float)):
                            entry_date = datetime.fromtimestamp(entry_timestamp)
                        elif entry_timestamp.isdigit():
                            entry_date = datetime.fromtimestamp(int(entry_timestamp))
                        else:
                            entry_date = datetime.strptime(entry_timestamp, "%Y%m%dT%H%M%SZ")
                        date_str = entry_date.strftime("%Y-%m-%d")
                        daily_pending[date_str] += 1
                        
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                continue
                
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        return {}, {}
    
    return daily_completed, daily_pending

def generate_chart_data(daily_completed, daily_pending, days):
    """Generate chart data for specified number of days"""
    today = datetime.now()
    dates = []
    completed_counts = []
    pending_counts = []
    
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        if days <= 7:
            dates.append(date.strftime("%a %m/%d"))
        elif days <= 31:
            dates.append(date.strftime("%b %d"))
        else:
            dates.append(date.strftime("%m/%y"))
        completed_counts.append(daily_completed.get(date_str, 0))
        pending_counts.append(daily_pending.get(date_str, 0))
    
    return dates, completed_counts, pending_counts

def generate_heatmap_data(daily_completed):
    """Generate heatmap data organized by year"""
    heatmap_data = {}
    
    # Get all years that have data
    years = set()
    for date_str in daily_completed.keys():
        year = datetime.strptime(date_str, "%Y-%m-%d").year
        years.add(year)
    
    # Add current year if not present
    current_year = datetime.now().year
    years.add(current_year)
    
    for year in sorted(years):
        year_data = {}
        
        # Generate all dates for the year
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            count = daily_completed.get(date_str, 0)
            year_data[date_str] = count
            current_date += timedelta(days=1)
        
        heatmap_data[str(year)] = year_data
    
    return heatmap_data

def generate_html(daily_completed, daily_pending):
    """Generate HTML dashboard with Chart.js"""
    
    # Generate data for different time periods
    week_dates, week_completed, week_pending = generate_chart_data(daily_completed, daily_pending, 7)
    month_dates, month_completed, month_pending = generate_chart_data(daily_completed, daily_pending, 30)
    
    # Calculate full history range
    all_dates = sorted(set(list(daily_completed.keys()) + list(daily_pending.keys())))
    if all_dates:
        start_date = datetime.strptime(all_dates[0], "%Y-%m-%d")
        end_date = datetime.now()
        full_days = (end_date - start_date).days + 1
        full_dates, full_completed, full_pending = generate_chart_data(daily_completed, daily_pending, full_days)
    else:
        full_dates, full_completed, full_pending = [], [], []
    
    # Generate heatmap data
    heatmap_data = generate_heatmap_data(daily_completed)
    
    # Calculate last year's tasks
    current_year = datetime.now().year
    last_year_data = heatmap_data.get(str(current_year), {})
    last_year_total = sum(last_year_data.values())
    
    total_tasks = sum(daily_completed.values())
    avg_daily = round(sum(month_completed) / len(month_completed), 1) if month_completed else 0
    current_pending = sum(daily_pending.values())
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Caleb's Task Tracking Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {{
            font-family: "ETBook", Palatino, "Palatino Linotype", "Palatino LT STD", "Book Antiqua", Georgia, serif;
            max-width: 55rem;
            margin: 2rem auto;
            padding: 0 1rem;
            background: #fffff8;
            color: #111;
            line-height: 1.4;
        }}
        .header {{
            margin-bottom: 3rem;
            border-bottom: 1px solid #ccc;
            padding-bottom: 1rem;
        }}
        .header h1 {{
            font-weight: 400;
            font-size: 2.5rem;
            margin: 0 0 0.5rem 0;
            color: #111;
        }}
        .header p {{
            margin: 0;
            font-size: 1.1rem;
            color: #666;
            font-style: italic;
        }}
        .stats {{
            margin-bottom: 3rem;
            display: flex;
            justify-content: space-between;
            gap: 2rem;
        }}
        .stat-card {{
            flex: 1;
            text-align: left;
            border-right: 1px solid #ddd;
            padding-right: 2rem;
        }}
        .stat-card:last-child {{
            border-right: none;
            padding-right: 0;
        }}
        .stat-number {{
            font-size: 3rem;
            font-weight: 400;
            color: #111;
            margin: 0;
            line-height: 1;
        }}
        .stat-label {{
            color: #666;
            margin-top: 0.25rem;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .chart-container {{
            margin-bottom: 2rem;
        }}
        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        .chart-container h2 {{
            font-size: 1.2rem;
            font-weight: 400;
            margin: 0;
            color: #111;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.9rem;
        }}
        .time-selector {{
            display: flex;
            gap: 0.5rem;
        }}
        .time-button {{
            background: none;
            border: 1px solid #ccc;
            color: #666;
            padding: 0.25rem 0.75rem;
            font-size: 0.8rem;
            font-family: inherit;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            transition: all 0.2s ease;
        }}
        .time-button:hover {{
            border-color: #111;
            color: #111;
        }}
        .time-button.active {{
            background: #111;
            color: #fff;
            border-color: #111;
        }}
        .heatmap-container {{
            margin-bottom: 3rem;
        }}
        .heatmap-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        .heatmap-container h2 {{
            font-size: 1.2rem;
            font-weight: 400;
            margin: 0;
            color: #111;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.9rem;
        }}
        .year-selector {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .year-button {{
            background: none;
            border: none;
            color: #666;
            font-size: 1.2rem;
            cursor: pointer;
            padding: 0.25rem;
            transition: color 0.2s ease;
        }}
        .year-button:hover {{
            color: #111;
        }}
        .year-button:disabled {{
            color: #ccc;
            cursor: not-allowed;
        }}
        .current-year {{
            font-size: 0.9rem;
            color: #111;
            font-weight: 400;
            min-width: 3rem;
            text-align: center;
        }}
        .heatmap-calendar {{
            display: flex;
            gap: 3px;
            overflow-x: auto;
            padding: 1rem 0;
        }}
        .heatmap-grid {{
            display: grid;
            grid-template-columns: repeat(53, 11px);
            grid-template-rows: repeat(7, 11px);
            gap: 3px;
            grid-auto-flow: column;
        }}
        .month-headers {{
            display: flex;
            gap: 3px;
            margin-bottom: 0.5rem;
        }}
        .month-header {{
            font-size: 0.7rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            text-align: center;
            height: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 11px;
        }}
        .day-labels {{
            display: flex;
            flex-direction: column;
            gap: 3px;
            margin-right: 10px;
            font-size: 0.7rem;
            color: #666;
        }}
        .day-label {{
            height: 11px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 5px;
        }}
        .heatmap-square {{
            width: 11px;
            height: 11px;
            border-radius: 2px;
            cursor: pointer;
            transition: all 0.1s ease;
        }}
        .heatmap-square:hover {{
            outline: 1px solid #1f2328;
            outline-offset: 1px;
        }}
        .level-0 {{ background-color: #ebedf0; }}
        .level-1 {{ background-color: #9be9a8; }}
        .level-2 {{ background-color: #40c463; }}
        .level-3 {{ background-color: #30a14e; }}
        .level-4 {{ background-color: #216e39; }}
        .heatmap-legend {{
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 0.5rem;
            margin-top: 1rem;
            font-size: 0.7rem;
            color: #666;
        }}
        .legend-scale {{
            display: flex;
            gap: 2px;
        }}
        .legend-square {{
            width: 10px;
            height: 10px;
            border: 1px solid #eee;
        }}
        .heatmap-tooltip {{
            position: absolute;
            background: #111;
            color: #fff;
            padding: 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            pointer-events: none;
            z-index: 100;
            opacity: 0;
            transition: opacity 0.2s ease;
        }}
        .footer {{
            border-top: 1px solid #ccc;
            padding-top: 1rem;
            color: #999;
            font-size: 0.8rem;
            text-align: right;
        }}
        @media (max-width: 768px) {{
            .stats {{
                flex-direction: column;
                gap: 1rem;
            }}
            .stat-card {{
                border-right: none;
                border-bottom: 1px solid #ddd;
                padding-right: 0;
                padding-bottom: 1rem;
            }}
            .stat-card:last-child {{
                border-bottom: none;
                padding-bottom: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Caleb's Task Tracking Dashboard</h1>
        <p>Daily task completion tracking</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{total_tasks}</div>
            <div class="stat-label">Total Completed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{avg_daily}</div>
            <div class="stat-label">Daily Average (30 days)</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{month_completed[-1] if month_completed else 0}</div>
            <div class="stat-label">Completed Today</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{current_pending}</div>
            <div class="stat-label">Pending Tasks</div>
        </div>
    </div>

    <div class="chart-container">
        <div class="chart-header">
            <h2>Daily Task Activity</h2>
            <div class="time-selector">
                <button class="time-button" onclick="updateChart('week')">Week</button>
                <button class="time-button active" onclick="updateChart('month')">Month</button>
                <button class="time-button" onclick="updateChart('full')">Full</button>
            </div>
        </div>
        <canvas id="tasksChart"></canvas>
    </div>

    <div class="heatmap-container">
        <div class="heatmap-header">
            <h2>{last_year_total} tasks done in the last year</h2>
            <div class="year-selector">
                <button class="year-button" onclick="changeYear(-1)">‹</button>
                <span class="current-year" id="currentYear">2025</span>
                <button class="year-button" onclick="changeYear(1)">›</button>
            </div>
        </div>
        <div class="heatmap-calendar">
            <div class="day-labels">
                <div class="month-header"></div>
                <div class="day-label">Mon</div>
                <div class="day-label"></div>
                <div class="day-label">Wed</div>
                <div class="day-label"></div>
                <div class="day-label">Fri</div>
                <div class="day-label"></div>
            </div>
            <div>
                <div class="month-headers" id="monthHeaders">
                    <!-- Month headers will be generated by JavaScript -->
                </div>
                <div class="heatmap-grid" id="heatmapCalendar">
                    <!-- Calendar grid will be generated by JavaScript -->
                </div>
            </div>
        </div>
        <div class="heatmap-legend">
            <span>Less</span>
            <div class="legend-scale">
                <div class="legend-square level-0"></div>
                <div class="legend-square level-1"></div>
                <div class="legend-square level-2"></div>
                <div class="legend-square level-3"></div>
                <div class="legend-square level-4"></div>
            </div>
            <span>More</span>
        </div>
    </div>
    <div class="heatmap-tooltip" id="heatmapTooltip"></div>

    <div class="footer">
        <p>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</p>
    </div>

    <script>
        // Data for different time periods
        const chartData = {{
            week: {{
                labels: {json.dumps(week_dates)},
                completed: {json.dumps(week_completed)},
                pending: {json.dumps(week_pending)}
            }},
            month: {{
                labels: {json.dumps(month_dates)},
                completed: {json.dumps(month_completed)},
                pending: {json.dumps(month_pending)}
            }},
            full: {{
                labels: {json.dumps(full_dates)},
                completed: {json.dumps(full_completed)},
                pending: {json.dumps(full_pending)}
            }}
        }};

        // Heatmap data organized by year
        const heatmapData = {json.dumps(heatmap_data)};
        let currentHeatmapYear = {datetime.now().year};

        const ctx = document.getElementById('tasksChart').getContext('2d');
        const chart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: chartData.month.labels,
                datasets: [{{
                    label: 'Completed',
                    data: chartData.month.completed,
                    borderColor: '#111',
                    backgroundColor: 'transparent',
                    borderWidth: 1,
                    fill: false,
                    tension: 0,
                    pointRadius: 2,
                    pointBackgroundColor: '#111',
                    pointBorderColor: '#111'
                }}, {{
                    label: 'Pending Added',
                    data: chartData.month.pending,
                    borderColor: '#666',
                    backgroundColor: 'transparent',
                    borderWidth: 1,
                    borderDash: [3, 3],
                    fill: false,
                    tension: 0,
                    pointRadius: 2,
                    pointBackgroundColor: '#666',
                    pointBorderColor: '#666'
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top',
                        labels: {{
                            color: '#666',
                            font: {{
                                size: 11
                            }},
                            usePointStyle: true,
                            padding: 15
                        }}
                    }},
                    title: {{
                        display: false
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{
                            display: false
                        }},
                        border: {{
                            display: false
                        }},
                        ticks: {{
                            color: '#666',
                            font: {{
                                size: 11
                            }}
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        grid: {{
                            color: '#eee',
                            borderDash: [2, 2]
                        }},
                        border: {{
                            display: false
                        }},
                        ticks: {{
                            stepSize: 1,
                            color: '#666',
                            font: {{
                                size: 11
                            }}
                        }}
                    }}
                }},
                elements: {{
                    point: {{
                        hoverRadius: 4
                    }}
                }}
            }}
        }});

        // Function to update chart based on time period
        function updateChart(period) {{
            // Update button states
            document.querySelectorAll('.time-button').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            // Update chart data
            chart.data.labels = chartData[period].labels;
            chart.data.datasets[0].data = chartData[period].completed;
            chart.data.datasets[1].data = chartData[period].pending;
            chart.update();
        }}

        // Function to get intensity level based on task count
        function getIntensityLevel(count) {{
            if (count === 0) return 0;
            if (count === 1) return 1;
            if (count <= 3) return 2;
            if (count <= 5) return 3;
            return 4;
        }}

        // Function to render heatmap for current year
        function renderHeatmap() {{
            const calendar = document.getElementById('heatmapCalendar');
            const monthHeaders = document.getElementById('monthHeaders');
            const yearData = heatmapData[currentHeatmapYear.toString()] || {{}};
            
            calendar.innerHTML = '';
            monthHeaders.innerHTML = '';
            
            // Get the first day of the year and calculate the start of the grid
            const yearStart = new Date(currentHeatmapYear, 0, 1);
            const startDay = yearStart.getDay(); // 0 = Sunday, 1 = Monday, etc.
            
            // Calculate the start date for the grid (might be from previous year)
            const gridStart = new Date(yearStart);
            gridStart.setDate(yearStart.getDate() - (startDay === 0 ? 6 : startDay - 1)); // Start on Monday
            
            // Generate month headers (53 weeks)
            const totalWeeks = 53;
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            
            for (let week = 0; week < totalWeeks; week++) {{
                const weekStart = new Date(gridStart);
                weekStart.setDate(gridStart.getDate() + week * 7);
                
                const monthHeader = document.createElement('div');
                monthHeader.className = 'month-header';
                
                // Show month label if this is the first week of the month
                if (weekStart.getDate() <= 7 && weekStart.getFullYear() === currentHeatmapYear) {{
                    monthHeader.textContent = months[weekStart.getMonth()];
                }}
                monthHeaders.appendChild(monthHeader);
            }}
            
            // Generate all squares in grid order (week by week)
            for (let week = 0; week < totalWeeks; week++) {{
                for (let day = 0; day < 7; day++) {{
                    const currentDate = new Date(gridStart);
                    currentDate.setDate(gridStart.getDate() + week * 7 + day);
                    
                    const square = document.createElement('div');
                    square.className = 'heatmap-square';
                    
                    // Only show data for the current year
                    if (currentDate.getFullYear() === currentHeatmapYear) {{
                        const dateStr = currentDate.toISOString().split('T')[0];
                        const count = yearData[dateStr] || 0;
                        const level = getIntensityLevel(count);
                        
                        square.classList.add(`level-${{level}}`);
                        square.dataset.date = dateStr;
                        square.dataset.count = count;
                        
                        // Add hover events
                        square.addEventListener('mouseenter', showTooltip);
                        square.addEventListener('mouseleave', hideTooltip);
                    }} else {{
                        // Dates from previous/next year - show as empty
                        square.classList.add('level-0');
                        square.style.opacity = '0.3';
                    }}
                    
                    calendar.appendChild(square);
                }}
            }}
        }}

        // Tooltip functions
        function showTooltip(event) {{
            const tooltip = document.getElementById('heatmapTooltip');
            const date = event.target.dataset.date;
            const count = event.target.dataset.count;
            
            if (date) {{
                const dateObj = new Date(date);
                const formattedDate = dateObj.toLocaleDateString('en-US', {{
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                }});
                
                tooltip.innerHTML = `${{formattedDate}}<br>${{count}} task${{count !== '1' ? 's' : ''}} completed`;
                tooltip.style.opacity = '1';
                
                const rect = event.target.getBoundingClientRect();
                tooltip.style.left = rect.left + window.scrollX - tooltip.offsetWidth / 2 + rect.width / 2 + 'px';
                tooltip.style.top = rect.top + window.scrollY - tooltip.offsetHeight - 5 + 'px';
            }}
        }}

        function hideTooltip() {{
            const tooltip = document.getElementById('heatmapTooltip');
            tooltip.style.opacity = '0';
        }}

        // Year navigation
        function changeYear(delta) {{
            const availableYears = Object.keys(heatmapData).map(y => parseInt(y)).sort();
            const currentIndex = availableYears.indexOf(currentHeatmapYear);
            const newIndex = currentIndex + delta;
            
            if (newIndex >= 0 && newIndex < availableYears.length) {{
                currentHeatmapYear = availableYears[newIndex];
                document.getElementById('currentYear').textContent = currentHeatmapYear;
                renderHeatmap();
            }}
        }}

        // Initialize heatmap
        document.addEventListener('DOMContentLoaded', function() {{
            renderHeatmap();
        }});
    </script>
</body>
</html>"""
    
    return html

def main():
    daily_completed, daily_pending = parse_taskwarrior_data()
    html = generate_html(daily_completed, daily_pending)
    print(html)

if __name__ == "__main__":
    main()