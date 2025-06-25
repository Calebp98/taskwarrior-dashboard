#!/usr/bin/env python3
import matplotlib.pyplot as plt
import subprocess
from datetime import datetime, timedelta

def get_task_completion_data():
    """Get task completion data for the past 7 days from TaskWarrior"""
    data = {}
    
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        # Get completed tasks for this specific date
        cmd = f"task completed end:{date_str}"
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            # Count lines that start with numbers (task entries)
            task_lines = [line for line in result.stdout.split('\n') if line.strip() and line[0].isdigit()]
            count = len(task_lines)
        except:
            count = 0
            
        data[date_str] = count
    
    return data

def create_graph(data):
    """Create a simple bar graph of task completions"""
    dates = sorted(data.keys())
    counts = [data[date] for date in dates]
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(dates, counts, color='steelblue', alpha=0.7)
    
    # Add value labels on bars
    for bar, count in zip(bars, counts):
        if count > 0:
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                    str(count), ha='center', va='bottom')
    
    plt.title('TaskWarrior Completed Tasks - Past 7 Days', fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Tasks Completed', fontsize=12)
    plt.xticks(rotation=45)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    # Show the graph
    plt.show()
    
    # Also save it
    plt.savefig('taskwarrior_completion_graph.png', dpi=300, bbox_inches='tight')

if __name__ == "__main__":
    print("Fetching TaskWarrior completion data...")
    data = get_task_completion_data()
    
    print("Daily completion summary:")
    for date in sorted(data.keys()):
        print(f"{date}: {data[date]} tasks")
    
    print("\nGenerating graph...")
    create_graph(data)
    print("Graph saved as 'taskwarrior_completion_graph.png'")