from flask import Flask, Response, request, jsonify
import json
import requests
import urllib.parse
from datetime import datetime, timedelta
import re

app = Flask(__name__)

class TemperatureService:
    def __init__(self):
        self.base_url = "https://wttr.in"
    
    def get_temperature_data(self, location, days=5):
        """Get temperature data for the past N days"""
        try:
            # Get weather data in JSON format
            url = f"{self.base_url}/{urllib.parse.quote(location)}?format=j1"
            headers = {
                'User-Agent': 'curl/7.68.0',  # wttr.in works better with curl user agent
                'Accept': 'application/json'
            }
            
            print(f"DEBUG: Requesting URL: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Debug response
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response content type: {response.headers.get('content-type', 'unknown')}")
            print(f"DEBUG: Response content length: {len(response.text)}")
            print(f"DEBUG: First 200 chars of response: {response.text[:200]}")
            
            # Check if response is empty or contains error message
            if not response.text.strip():
                raise Exception("Empty response from weather service")
            
            # Check for rate limit or error messages
            if "We have temporary problems" in response.text or "503 Service Unavailable" in response.text:
                raise Exception("Weather service is temporarily unavailable (rate limited)")
            
            # Check if response contains location error (plain text response)
            if "Unknown location" in response.text and "please try" in response.text:
                # Extract suggested coordinates if available
                coord_match = re.search(r'~([-\d.,]+)', response.text)
                suggested_coords = coord_match.group(1) if coord_match else "coordinates"
                raise Exception(f"Location '{location}' not recognized by weather service. Try using '{suggested_coords}' or a more specific location name like '{location}, Country'")
            
            # Try to parse JSON
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON decode error: {e}")
                print(f"DEBUG: Raw response: {response.text}")
                
                # Check if it's a plain text error message
                if response.text.strip().startswith('"') and response.text.strip().endswith('"'):
                    # It's a quoted string, likely an error message
                    error_msg = response.text.strip().strip('"')
                    raise Exception(f"Weather service error: {error_msg}")
                else:
                    raise Exception(f"Invalid JSON response from weather service. Raw response: {response.text[:100]}")
            
            # Validate JSON structure
            if not isinstance(data, dict):
                raise Exception("Invalid JSON structure from weather service")
            
            # Check for error in response
            if 'error' in data:
                raise Exception(f"Weather service error: {data['error']}")
            
            # Extract current and forecast data
            current = data.get('current_condition', [])
            weather_data = data.get('weather', [])
            
            if not current:
                raise Exception("No current weather data available")
            
            current = current[0]  # Get first (and usually only) current condition
            
            temperatures = []
            dates = []
            
            # Get today's temperature
            today_temp = int(current.get('temp_C', 0))
            today = datetime.now().strftime('%m-%d')
            temperatures.append(today_temp)
            dates.append(today)
            
            print(f"DEBUG: Current temperature: {today_temp}°C")
            print(f"DEBUG: Weather data entries: {len(weather_data)}")
            
            # Get forecast temperatures (next few days)
            for i, day_data in enumerate(weather_data[:days-1]):
                date_str = day_data.get('date', '')
                if date_str:
                    # Parse date and format as MM-DD
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        formatted_date = date_obj.strftime('%m-%d')
                        dates.append(formatted_date)
                    except ValueError:
                        dates.append(date_str[-5:] if len(date_str) >= 5 else f"Day{i+2}")
                else:
                    dates.append(f"Day{i+2}")
                
                # Get average temperature for the day
                hourly_data = day_data.get('hourly', [])
                if hourly_data:
                    # Calculate average from hourly data
                    temps = []
                    for hour in hourly_data:
                        temp_c = hour.get('tempC')
                        if temp_c is not None:
                            temps.append(int(temp_c))
                    
                    if temps:
                        avg_temp = sum(temps) // len(temps)
                        temperatures.append(avg_temp)
                    else:
                        # Fallback to min/max average
                        min_temp = int(day_data.get('mintempC', 0))
                        max_temp = int(day_data.get('maxtempC', 0))
                        avg_temp = (min_temp + max_temp) // 2
                        temperatures.append(avg_temp)
                else:
                    # Fallback to min/max average
                    min_temp = int(day_data.get('mintempC', 0))
                    max_temp = int(day_data.get('maxtempC', 0))
                    avg_temp = (min_temp + max_temp) // 2
                    temperatures.append(avg_temp)
                
                print(f"DEBUG: Day {i+1} ({dates[-1]}): {temperatures[-1]}°C")
            
            result = {
                'location': location,
                'dates': dates,
                'temperatures': temperatures,
                'unit': 'Celsius'
            }
            
            print(f"DEBUG: Final result: {result}")
            return result
            
        except Exception as e:
            raise Exception(f"Failed to get weather data: {str(e)}")
    
    def generate_chart_url(self, temp_data):
        """Generate QuickChart URL for temperature plot"""
        try:
            dates = temp_data['dates']
            temperatures = temp_data['temperatures']
            location = temp_data['location']
            
            # Create chart configuration
            chart_config = {
                "type": "line",
                "data": {
                    "labels": dates,
                    "datasets": [{
                        "label": f"Temperature ({location})",
                        "data": temperatures,
                        "borderColor": "rgb(75, 192, 192)",
                        "backgroundColor": "rgba(75, 192, 192, 0.2)",
                        "tension": 0.4,
                        "fill": True
                    }]
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"Temperature Trend - {location}"
                        },
                        "legend": {
                            "display": True
                        }
                    },
                    "scales": {
                        "y": {
                            "beginAtZero": False,
                            "title": {
                                "display": True,
                                "text": "Temperature (°C)"
                            }
                        },
                        "x": {
                            "title": {
                                "display": True,
                                "text": "Date (MM-DD)"
                            }
                        }
                    }
                }
            }
            
            # Encode chart config for URL
            chart_json = json.dumps(chart_config)
            encoded_chart = urllib.parse.quote(chart_json)
            
            # Generate QuickChart URL
            chart_url = f"https://quickchart.io/chart?c={encoded_chart}&width=800&height=400"
            
            return chart_url
            
        except Exception as e:
            raise Exception(f"Failed to generate chart URL: {str(e)}")

# Initialize service
temp_service = TemperatureService()

@app.route('/temperature-plot-stream')
def temperature_plot_stream():
    """SSE endpoint for temperature plot requests"""
    location = request.args.get('location', 'New York')
    days = min(int(request.args.get('days', 5)), 7)  # Max 7 days
    
    def generate():
        try:
            # Send initial connection event
            yield f"event: connection\n"
            yield f"data: {json.dumps({'status': 'connected', 'location': location})}\n\n"
            
            # Send fetching status
            yield f"event: status\n"
            yield f"data: {json.dumps({'status': 'fetching_data', 'message': f'Getting weather data for {location}'})}\n\n"
            
            # Get temperature data
            temp_data = temp_service.get_temperature_data(location, days)
            
            # Send temperature data
            yield f"event: temperature_data\n"
            yield f"data: {json.dumps(temp_data)}\n\n"
            
            # Send chart generation status
            yield f"event: status\n"
            yield f"data: {json.dumps({'status': 'generating_chart', 'message': 'Creating temperature plot'})}\n\n"
            
            # Generate chart URL
            chart_url = temp_service.generate_chart_url(temp_data)
            
            # Send final result
            result = {
                'status': 'completed',
                'location': location,
                'chart_url': chart_url,
                'temperature_data': temp_data,
                'timestamp': datetime.now().isoformat()
            }
            
            yield f"event: result\n"
            yield f"data: {json.dumps(result)}\n\n"
            
        except Exception as e:
            error_result = {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            yield f"event: error\n"
            yield f"data: {json.dumps(error_result)}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )

@app.route('/api/temperature-plot')
def temperature_plot_api():
    """REST API endpoint for temperature plot (non-SSE)"""
    location = request.args.get('location', 'New York')
    days = min(int(request.args.get('days', 5)), 7)
    
    try:
        temp_data = temp_service.get_temperature_data(location, days)
        chart_url = temp_service.generate_chart_url(temp_data)
        
        return jsonify({
            'status': 'success',
            'location': location,
            'chart_url': chart_url,
            'temperature_data': temp_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/debug/weather')
def debug_weather():
    """Debug endpoint to test wttr.in API response"""
    location = request.args.get('location', 'New York')
    
    try:
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=j1"
        headers = {
            'User-Agent': 'curl/7.68.0',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        return jsonify({
            'url': url,
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'content_type': response.headers.get('content-type', 'unknown'),
            'content_length': len(response.text),
            'raw_content': response.text[:1000],  # First 1000 chars
            'is_json': response.headers.get('content-type', '').startswith('application/json')
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'url': url if 'url' in locals() else 'unknown'
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Temperature Plot SSE MCP Server',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def index():
    """API documentation"""
    return jsonify({
        'service': 'Temperature Plot SSE MCP Server',
        'description': 'Provides temperature data and QuickChart plot URLs via SSE',
        'endpoints': {
            '/temperature-plot-stream': {
                'method': 'GET',
                'description': 'SSE stream for temperature plot generation',
                'parameters': {
                    'location': 'Location name (default: New York)',
                    'days': 'Number of days (1-7, default: 5)'
                },
                'events': ['connection', 'status', 'temperature_data', 'result', 'error']
            },
            '/api/temperature-plot': {
                'method': 'GET',
                'description': 'REST API for temperature plot',
                'parameters': {
                    'location': 'Location name (default: New York)',
                    'days': 'Number of days (1-7, default: 5)'
                }
            },
            '/debug/weather': {
                'method': 'GET',
                'description': 'Debug wttr.in API response',
                'parameters': {
                    'location': 'Location name for testing (default: New York)'
                }
            },
            '/health': {
                'method': 'GET',
                'description': 'Health check endpoint'
            }
        },
        'data_source': 'https://wttr.in',
        'chart_service': 'https://quickchart.io'
    })

if __name__ == '__main__':
    print("Starting Temperature Plot SSE MCP Server")
    print("Endpoints:")
    print("  SSE Stream: http://localhost:8000/temperature-plot-stream?location=<city>")
    print("  REST API:   http://localhost:8000/api/temperature-plot?location=<city>")
    print("  Debug:      http://localhost:8000/debug/weather?location=<city>")
    print("  Health:     http://localhost:8000/health")
    print("  Docs:       http://localhost:8000/")
    app.run(debug=True, host='0.0.0.0', port=8000, threaded=True)