import json, aiohttp, logging, datetime
from aiohttp import web
from info import ADMINS, LOG_CHANNEL
from database.users_chats_db import db
from database.user_statistics import user_stats
from database.tiered_access import tiered_access, DEFAULT_TIERS
from utils import temp
from main.bot import MainBot
from pyrogram import enums
from jinja2 import Environment, FileSystemLoader
import os
import asyncio

# Create a directory for templates if it doesn't exist
os.makedirs('templates', exist_ok=True)

# Create admin dashboard template
ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Filter Bot Admin Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { padding-top: 20px; background-color: #f8f9fa; }
        .dashboard-card { margin-bottom: 20px; }
        .stat-card { height: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4 text-center">Filter Bot Admin Dashboard</h1>
        
        <div class="row">
            <div class="col">
                <div class="card dashboard-card">
                    <div class="card-header bg-primary text-white">
                        Overview
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <div class="card stat-card">
                                    <div class="card-body">
                                        <h5 class="card-title">Total Users</h5>
                                        <h2 class="card-text">{{ total_users }}</h2>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card stat-card">
                                    <div class="card-body">
                                        <h5 class="card-title">Total Files</h5>
                                        <h2 class="card-text">{{ total_files }}</h2>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card stat-card">
                                    <div class="card-body">
                                        <h5 class="card-title">Total Searches</h5>
                                        <h2 class="card-text">{{ total_searches }}</h2>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="card dashboard-card">
                    <div class="card-header bg-info text-white">
                        User Activity (Last 7 Days)
                    </div>
                    <div class="card-body">
                        <canvas id="activityChart"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card dashboard-card">
                    <div class="card-header bg-success text-white">
                        Premium Users by Tier
                    </div>
                    <div class="card-body">
                        <canvas id="tierChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="card dashboard-card">
                    <div class="card-header bg-warning text-dark">
                        Top Users by Requests
                    </div>
                    <div class="card-body">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>User ID</th>
                                    <th>Total Requests</th>
                                    <th>Total Searches</th>
                                    <th>Tier</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for user in top_users %}
                                <tr>
                                    <td>{{ user.user_id }}</td>
                                    <td>{{ user.total_file_requests }}</td>
                                    <td>{{ user.total_searches }}</td>
                                    <td>{{ user.tier }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card dashboard-card">
                    <div class="card-header bg-danger text-white">
                        Most Requested Files
                    </div>
                    <div class="card-body">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>File Name</th>
                                    <th>Requests</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for file in top_files %}
                                <tr>
                                    <td>{{ file.file_name }}</td>
                                    <td>{{ file.request_count }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col">
                <div class="card dashboard-card">
                    <div class="card-header bg-dark text-white">
                        Manage User Tiers
                    </div>
                    <div class="card-body">
                        <form id="userTierForm" class="row g-3">
                            <div class="col-md-4">
                                <label for="userId" class="form-label">User ID</label>
                                <input type="number" class="form-control" id="userId" required>
                            </div>
                            <div class="col-md-4">
                                <label for="tier" class="form-label">Tier</label>
                                <select class="form-select" id="tier" required>
                                    {% for tier in tiers %}
                                    <option value="{{ tier.tier_id }}">{{ tier.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label for="duration" class="form-label">Duration (days)</label>
                                <input type="number" class="form-control" id="duration" value="30">
                            </div>
                            <div class="col-12 mt-3">
                                <button type="submit" class="btn btn-primary">Update User Tier</button>
                            </div>
                        </form>
                        <div id="updateResult" class="mt-3"></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col">
                <div class="card dashboard-card">
                    <div class="card-header bg-secondary text-white">
                        Duplicate File Detection
                    </div>
                    <div class="card-body">
                        <button id="findDuplicates" class="btn btn-warning mb-3">Find Duplicate Files</button>
                        <div class="progress mb-3 d-none" id="duplicateProgress">
                            <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 100%"></div>
                        </div>
                        <div id="duplicatesResult" class="mt-3">
                            <p>Click the button to start searching for potential duplicate files.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // User Activity Chart
            const activityData = {{ activity_data|tojson }};
            const activityLabels = activityData.map(item => `${item._id.month}/${item._id.day}`);
            const activityCounts = activityData.map(item => item.count);
            
            new Chart(document.getElementById('activityChart'), {
                type: 'line',
                data: {
                    labels: activityLabels,
                    datasets: [{
                        label: 'User Activity',
                        data: activityCounts,
                        borderColor: 'rgba(75, 192, 192, 1)',
                        tension: 0.1,
                        fill: false
                    }]
                }
            });
            
            // Tier Distribution Chart
            const tierData = {{ tier_data|tojson }};
            const tierLabels = Object.keys(tierData);
            const tierCounts = Object.values(tierData);
            
            new Chart(document.getElementById('tierChart'), {
                type: 'pie',
                data: {
                    labels: tierLabels,
                    datasets: [{
                        data: tierCounts,
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.7)',
                            'rgba(54, 162, 235, 0.7)',
                            'rgba(255, 206, 86, 0.7)',
                            'rgba(75, 192, 192, 0.7)',
                            'rgba(153, 102, 255, 0.7)'
                        ]
                    }]
                }
            });
            
            // User Tier Form
            document.getElementById('userTierForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                const userId = document.getElementById('userId').value;
                const tier = document.getElementById('tier').value;
                const duration = document.getElementById('duration').value;
                const resultDiv = document.getElementById('updateResult');
                
                resultDiv.innerHTML = '<div class="alert alert-info">Processing...</div>';
                
                try {
                    const response = await fetch('/admin/api/update_user_tier', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_id: userId, tier_id: tier, duration: duration})
                    });
                    
                    const data = await response.json();
                    if(data.success) {
                        resultDiv.innerHTML = `<div class="alert alert-success">Successfully updated user ${userId} to tier ${tier} for ${duration} days.</div>`;
                    } else {
                        resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                    }
                } catch(err) {
                    resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
                }
            });
            
            // Find Duplicates
            document.getElementById('findDuplicates').addEventListener('click', async function() {
                const progressBar = document.getElementById('duplicateProgress');
                const resultDiv = document.getElementById('duplicatesResult');
                
                progressBar.classList.remove('d-none');
                resultDiv.innerHTML = '<p>Searching for duplicates, please wait...</p>';
                
                try {
                    const response = await fetch('/admin/api/find_duplicates');
                    const data = await response.json();
                    
                    progressBar.classList.add('d-none');
                    
                    if(data.success) {
                        if(data.duplicates.length === 0) {
                            resultDiv.innerHTML = '<div class="alert alert-info">No potential duplicates found.</div>';
                        } else {
                            let html = '<div class="alert alert-warning">' + data.duplicates.length + ' potential duplicates found.</div>';
                            html += '<table class="table table-striped"><thead><tr><th>File 1</th><th>File 2</th><th>Actions</th></tr></thead><tbody>';
                            
                            data.duplicates.forEach(pair => {
                                html += `<tr>
                                    <td>${pair.file1.file_name}</td>
                                    <td>${pair.file2.file_name}</td>
                                    <td>
                                        <button class="btn btn-sm btn-danger">Delete</button>
                                        <button class="btn btn-sm btn-secondary">Ignore</button>
                                    </td>
                                </tr>`;
                            });
                            
                            html += '</tbody></table>';
                            resultDiv.innerHTML = html;
                        }
                    } else {
                        resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                    }
                } catch(err) {
                    progressBar.classList.add('d-none');
                    resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${err.message}</div>`;
                }
            });
        });
    </script>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Write template to file
with open('templates/admin_dashboard.html', 'w') as f:
    f.write(ADMIN_DASHBOARD_TEMPLATE)

# Set up Jinja2 environment
jinja_env = Environment(loader=FileSystemLoader('templates'))

# List of API routes to be added to the app
admin_routes = web.RouteTableDef()

# Authentication middleware
@web.middleware
async def auth_middleware(request, handler):
    """Middleware to check if user is authorized to access admin dashboard"""
    # Admin dashboard routes start with /admin/
    if request.path.startswith('/admin/'):
        # Check if user is authenticated
        # For now, we'll use a simple API key in the query string
        api_key = request.query.get('api_key')
        
        # This is a very basic authentication method - in production, you should use
        # proper authentication like JWT or session cookies
        if not api_key or not await is_valid_api_key(api_key):
            return web.json_response({"error": "Unauthorized"}, status=401)
    
    return await handler(request)

async def is_valid_api_key(api_key):
    """Check if the provided API key is valid"""
    # In production, you would look up the API key in your database
    # For now, we'll just check if it's a hardcoded value
    # This should be replaced with a better authentication system
    VALID_API_KEY = "filterbot_admin_123456"  # Change this to something secure
    return api_key == VALID_API_KEY

@admin_routes.get('/admin/dashboard')
async def admin_dashboard(request):
    """Admin dashboard main page"""
    try:
        # Get basic statistics
        total_users = await db.total_users_count()
        total_files = 0  # You would need to implement a way to count files
        
        # Get top users
        top_users = await user_stats.get_top_users_by_requests(10)
        
        # Add tier information to each user
        for user in top_users:
            user['tier'] = await tiered_access.get_user_tier(user['user_id'])
        
        # Get top files
        top_files = await user_stats.get_top_files(10)
        
        # Get activity data
        activity_data = await user_stats.get_activity_by_time(days=7)
        
        # Get tier distribution
        all_users = await db.get_all_users()
        tier_data = {'free': 0}
        for tier in DEFAULT_TIERS:
            if tier != 'free':  # We already initialized 'free'
                tier_data[tier] = 0
                
        async for user in all_users:
            tier = await tiered_access.get_user_tier(user['id'])
            if tier in tier_data:
                tier_data[tier] += 1
            else:
                tier_data[tier] = 1
        
        # Get total searches (this would need to be implemented in your stats system)
        total_searches = 0
        
        # Get all tiers
        tiers = await tiered_access.get_all_tiers()
        
        # Render template with data
        template = jinja_env.get_template('admin_dashboard.html')
        html_content = template.render(
            total_users=total_users,
            total_files=total_files,
            total_searches=total_searches,
            top_users=top_users,
            top_files=top_files,
            activity_data=activity_data,
            tier_data=tier_data,
            tiers=tiers
        )
        
        return web.Response(text=html_content, content_type='text/html')
    except Exception as e:
        logging.error(f"Error in admin dashboard: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)

@admin_routes.post('/admin/api/update_user_tier')
async def update_user_tier(request):
    """API endpoint to update a user's tier"""
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        tier_id = data.get('tier_id')
        duration_days = int(data.get('duration', 30))
        
        # Convert days to seconds
        duration_seconds = duration_days * 24 * 60 * 60
        
        # Update user tier
        success = await tiered_access.set_user_tier(user_id, tier_id, duration_seconds)
        
        # Send notification to user
        try:
            tier = await tiered_access.get_tier(tier_id)
            tier_name = tier.get('name', tier_id)
            
            message = f"🎉 Your subscription has been updated to **{tier_name}** tier for {duration_days} days!"
            await MainBot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=enums.ParseMode.MARKDOWN
            )
            
            # Also log this action
            log_message = f"Admin updated user {user_id} to tier {tier_id} ({tier_name}) for {duration_days} days"
            await MainBot.send_message(
                chat_id=LOG_CHANNEL,
                text=log_message
            )
        except Exception as e:
            logging.error(f"Failed to send notification: {str(e)}")
        
        return web.json_response({"success": True})
    except Exception as e:
        logging.error(f"Error updating user tier: {str(e)}")
        return web.json_response({"success": False, "error": str(e)})

@admin_routes.get('/admin/api/find_duplicates')
async def find_duplicates(request):
    """API endpoint to find potential duplicate files"""
    try:
        # Get similarity threshold from query string, default to 0.8
        similarity_threshold = float(request.query.get('threshold', 0.8))
        
        # Find duplicates
        duplicates = await user_stats.find_duplicate_files(similarity_threshold)
        
        return web.json_response({
            "success": True,
            "duplicates": duplicates
        })
    except Exception as e:
        logging.error(f"Error finding duplicates: {str(e)}")
        return web.json_response({"success": False, "error": str(e)})

@admin_routes.get('/admin/api/bulk_export')
async def bulk_export(request):
    """API endpoint to export all file data"""
    try:
        # This would be a heavy operation - you might want to implement pagination
        # or limit this to a specific query
        
        # For now, we'll just return a message
        return web.json_response({
            "success": True,
            "message": "Bulk export feature coming soon!"
        })
    except Exception as e:
        logging.error(f"Error in bulk export: {str(e)}")
        return web.json_response({"success": False, "error": str(e)})

async def register_admin_routes(app):
    """Register admin dashboard routes to the main app"""
    app.add_routes(admin_routes)
    # Apply auth middleware
    app.middlewares.append(auth_middleware) 