#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import sys

def parse_taskwarrior_data():
    """Parse completed tasks from Task Warrior's SQLite database"""
    db_file = os.path.expanduser("~/.task/taskchampion.sqlite3")
    
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found", file=sys.stderr)
        return {}
    
    daily_counts = Counter()
    
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
                    
                    # Check if task is completed and has end timestamp
                    if task_data.get('status') == 'completed' and 'end' in task_data:
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
                        daily_counts[date_str] += 1
                        
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                continue
                
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        return {}
    
    return daily_counts

def generate_html(daily_counts):
    """Generate HTML dashboard with Chart.js"""
    
    # Get last 30 days for the chart
    today = datetime.now()
    dates = []
    counts = []
    
    for i in range(29, -1, -1):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        dates.append(date.strftime("%b %d"))
        counts.append(daily_counts.get(date_str, 0))
    
    total_tasks = sum(daily_counts.values())
    avg_daily = round(sum(counts) / len(counts), 1)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Warrior Dashboard</title>
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
        .chart-container h2 {{
            font-size: 1.2rem;
            font-weight: 400;
            margin: 0 0 1rem 0;
            color: #111;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.9rem;
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
        <h1>Task Warrior Dashboard</h1>
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
            <div class="stat-number">{counts[-1] if counts else 0}</div>
            <div class="stat-label">Today</div>
        </div>
    </div>

    <div class="chart-container">
        <h2>Daily Task Completion (Last 30 Days)</h2>
        <canvas id="tasksChart"></canvas>
    </div>

    <div class="footer">
        <p>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}</p>
    </div>

    <script>
        const ctx = document.getElementById('tasksChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(dates)},
                datasets: [{{
                    label: 'Tasks',
                    data: {json.dumps(counts)},
                    borderColor: '#111',
                    backgroundColor: 'transparent',
                    borderWidth: 1,
                    fill: false,
                    tension: 0,
                    pointRadius: 2,
                    pointBackgroundColor: '#111',
                    pointBorderColor: '#111'
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: false
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
    </script>
</body>
</html>"""
    
    return html

def main():
    daily_counts = parse_taskwarrior_data()
    html = generate_html(daily_counts)
    print(html)

if __name__ == "__main__":
    main()