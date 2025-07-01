import json
import argparse

def generate_html(json_data):
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Game Completion Table</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .controls {{
            margin: 20px 0;
            padding: 15px;
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background-color: #fff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f2f2f2;
            cursor: pointer;
            position: relative;
        }}
        th:hover {{
            background-color: #e6e6e6;
        }}
        th.sort-asc::after {{
            content: " ↑";
        }}
        th.sort-desc::after {{
            content: " ↓";
        }}
        tr:hover {{
            background-color: #f9f9f9;
        }}
        .completed {{
            color: green;
            font-weight: bold;
        }}
        .dropped {{
            color: red;
            font-weight: bold;
        }}
        select, input {{
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #ddd;
            min-width: 120px;
        }}
        button {{
            padding: 8px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        button:hover {{
            background-color: #45a049;
        }}
        .no-results {{
            text-align: center;
            padding: 20px;
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>Game Completion Tracker</h1>
    
    <div class="controls">
        <select id="playerFilter">
            <option value="">All Players</option>
            <option value="P">Player P</option>
            <option value="T">Player T</option>
            <option value="R">Player R</option>
        </select>
        
        <select id="statusFilter">
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="dropped">Dropped</option>
        </select>
        
        <select id="platformFilter">
            <option value="">All Platforms</option>
        </select>
        
        <input type="text" id="gameSearch" placeholder="Search by game name...">
        
        <button id="resetFilters">Reset Filters</button>
    </div>
    
    <table id="gamesTable">
        <thead>
            <tr>
                <th data-column="player">Player</th>
                <th data-column="game">Game</th>
                <th data-column="month">Month</th>
                <th data-column="year">Year</th>
                <th data-column="platform">Platform</th>
                <th data-column="status">Status</th>
                <th data-column="co-op">Co-op Partners</th>
            </tr>
        </thead>
        <tbody id="tableBody">
            <!-- Data will be inserted here by JavaScript -->
        </tbody>
    </table>
    
    <script>
        // Load data from embedded JSON
        const originalData = {json.dumps(json_data, indent=2)};
        let currentData = [...originalData];
        
        // DOM elements
        const tableBody = document.getElementById('tableBody');
        const playerFilter = document.getElementById('playerFilter');
        const statusFilter = document.getElementById('statusFilter');
        const platformFilter = document.getElementById('platformFilter');
        const gameSearch = document.getElementById('gameSearch');
        const resetBtn = document.getElementById('resetFilters');
        
        // Initialize platform filter options
        function initPlatformFilter() {{
            const platforms = [...new Set(originalData.map(item => item.platform))];
            platforms.sort().forEach(platform => {{
                const option = document.createElement('option');
                option.value = platform;
                option.textContent = platform;
                platformFilter.appendChild(option);
            }});
        }}
        
        // Render table with current data
        function renderTable() {{
            tableBody.innerHTML = '';

            currentData.sort((a, b) => {{
                return b.id - a.id; // Sort by ID descending
                if (b.year !== a.year) {{
                    return b.year - a.year; // Sort by year descending
                }}
                return b.month - a.month; // Sort by month descending
            }});
            
            if (currentData.length === 0) {{
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="7" class="no-results">No games match your filters</td>';
                tableBody.appendChild(row);
                return;
            }}
            
            currentData.forEach(item => {{
                const row = document.createElement('tr');
                
                // Handle co-op partners display
                let coopDisplay = 'No';
                if (item['co-op'] && Array.isArray(item['co-op'])) {{
                    if (item['co-op'].length > 0) {{
                        coopDisplay = item['co-op'].join(', ');
                    }}
                }} else if (item['co-op']) {{
                    // Backward compatibility with boolean/string values
                    coopDisplay = item['co-op'] === true ? 'Yes' : item['co-op'];
                }}
                
                row.innerHTML = `
                    <td>${{item.player}}</td>
                    <td>${{item.game}}</td>
                    <td>${{item.month}}</td>
                    <td>${{item.year}}</td>
                    <td>${{item.platform}}</td>
                    <td class="${{item.status}}">${{item.status.charAt(0).toUpperCase() + item.status.slice(1)}}</td>
                    <td>${{coopDisplay}}</td>
                `;
                
                tableBody.appendChild(row);
            }});
        }}
        
        // Filter data based on current filters
        function filterData() {{
            const playerValue = playerFilter.value;
            const statusValue = statusFilter.value;
            const platformValue = platformFilter.value;
            const searchValue = gameSearch.value.toLowerCase();
            
            currentData = originalData.filter(item => {{
                return (playerValue === '' || item.player === playerValue) &&
                       (statusValue === '' || item.status === statusValue) &&
                       (platformValue === '' || item.platform === platformValue) &&
                       (searchValue === '' || item.game.toLowerCase().includes(searchValue));
            }});
            
            renderTable();
        }}
        
        // Sort data by column
        function sortData(column, direction) {{
            currentData.sort((a, b) => {{
                // Handle numeric columns differently if needed
                if (column === 'month' || column === 'year') {{
                    return direction === 'asc' 
                        ? a[column] - b[column] 
                        : b[column] - a[column];
                }}
                
                // Special handling for co-op column
                if (column === 'co-op') {{
                    const aValue = Array.isArray(a[column]) ? a[column].length : 0;
                    const bValue = Array.isArray(b[column]) ? b[column].length : 0;
                    return direction === 'asc' ? aValue - bValue : bValue - aValue;
                }}
                
                // Standard string comparison
                const aValue = String(a[column]).toLowerCase();
                const bValue = String(b[column]).toLowerCase();
                
                return direction === 'asc'
                    ? aValue.localeCompare(bValue)
                    : bValue.localeCompare(aValue);
            }});
            
            renderTable();
        }}
        
        // Reset all filters
        function resetFilters() {{
            playerFilter.value = '';
            statusFilter.value = '';
            platformFilter.value = '';
            gameSearch.value = '';
            filterData();
        }}
        
        // Initialize the table
        function init() {{
            initPlatformFilter();
            filterData();
            
            // Set up event listeners
            playerFilter.addEventListener('change', filterData);
            statusFilter.addEventListener('change', filterData);
            platformFilter.addEventListener('change', filterData);
            gameSearch.addEventListener('input', filterData);
            resetBtn.addEventListener('click', resetFilters);
            
            // Set up sorting
            document.querySelectorAll('th[data-column]').forEach(th => {{
                th.addEventListener('click', () => {{
                    const column = th.getAttribute('data-column');
                    const currentDir = th.getAttribute('data-sort');
                    const newDir = currentDir === 'asc' ? 'desc' : 'asc';
                    
                    // Reset all sort indicators
                    document.querySelectorAll('th[data-column]').forEach(header => {{
                        header.removeAttribute('data-sort');
                    }});
                    
                    // Set new sort indicator
                    th.setAttribute('data-sort', newDir);
                    th.classList.add('sort-' + newDir);
                    
                    sortData(column, newDir);
                }});
            }});
        }}
        
        // Start the application
        document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
"""
    return html

def main():
    parser = argparse.ArgumentParser(description='Generate HTML from JSON game data')
    parser.add_argument('-i', '--input', required=True, help='Input JSON file path')
    parser.add_argument('-o', '--output', default='index.html', 
                        help='Output HTML file path (default: index.html)')
    
    args = parser.parse_args()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.input}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {args.input}")
        return

    html_content = generate_html(json_data)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML file generated successfully: {args.output}")

if __name__ == "__main__":
    main()
