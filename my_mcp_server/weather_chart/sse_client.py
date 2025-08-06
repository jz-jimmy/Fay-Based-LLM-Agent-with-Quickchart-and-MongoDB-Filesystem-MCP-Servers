import requests
import json
import urllib.parse
from datetime import datetime

class TemperaturePlotSSEClient:
    def __init__(self, server_url="http://localhost:5000"):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        
    def get_temperature_plot(self, location, days=5, callback=None):
        """
        Get temperature plot for a location via SSE stream
        
        Args:
            location: Location name (e.g., "New York", "London", "Tokyo")
            days: Number of days (1-7, default: 5)
            callback: Optional callback function for real-time updates
        
        Returns:
            dict: Final result with chart_url and temperature_data
        """
        # Prepare URL with parameters
        params = {
            'location': location,
            'days': min(max(days, 1), 7)  # Ensure days is between 1-7
        }
        url = f"{self.server_url}/temperature-plot-stream?" + urllib.parse.urlencode(params)
        
        print(f"Requesting temperature plot for: {location} ({days} days)")
        print(f"Connecting to: {url}")
        
        result = None
        
        try:
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            buffer = ""
            event_type = None
            
            for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
                if chunk:
                    buffer += chunk
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.rstrip('\r')
                        
                        if line.startswith('event:'):
                            event_type = line[6:].strip()
                        elif line.startswith('data:'):
                            data = line[5:].strip()
                            try:
                                parsed_data = json.loads(data)
                            except json.JSONDecodeError:
                                parsed_data = {'raw': data}
                            
                            # Handle different event types
                            if event_type == 'connection':
                                print(f"✓ Connected - Processing {parsed_data.get('location', location)}")
                            elif event_type == 'status':
                                status = parsed_data.get('status', 'unknown')
                                message = parsed_data.get('message', 'Processing...')
                                print(f"⏳ {message}")
                            elif event_type == 'temperature_data':
                                print(f"📊 Temperature data received:")
                                temps = parsed_data.get('temperatures', [])
                                dates = parsed_data.get('dates', [])
                                for date, temp in zip(dates, temps):
                                    print(f"   {date}: {temp}°C")
                            elif event_type == 'result':
                                print(f"✅ Plot generated successfully!")
                                result = parsed_data
                                chart_url = result.get('chart_url', '')
                                if chart_url:
                                    print(f"📈 Chart URL: {chart_url}")
                                break
                            elif event_type == 'error':
                                error_msg = parsed_data.get('error', 'Unknown error')
                                print(f"❌ Error: {error_msg}")
                                result = parsed_data
                                break
                            
                            # Call user callback if provided
                            if callback:
                                callback(event_type, parsed_data)
                            
                            event_type = None
                        elif line == '':
                            continue
                            
        except requests.exceptions.RequestException as e:
            error_result = {
                'status': 'error',
                'error': f'Connection error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
            print(f"❌ Connection error: {e}")
            return error_result
        except Exception as e:
            error_result = {
                'status': 'error',
                'error': f'Unexpected error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
            print(f"❌ Unexpected error: {e}")
            return error_result
        
        return result or {
            'status': 'error',
            'error': 'No result received',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_temperature_plot_sync(self, location, days=5):
        """
        Get temperature plot via REST API (synchronous)
        
        Args:
            location: Location name
            days: Number of days (1-7)
            
        Returns:
            dict: Result with chart_url and temperature_data
        """
        params = {
            'location': location,
            'days': min(max(days, 1), 7)
        }
        url = f"{self.server_url}/api/temperature-plot"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'error': f'Request failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def debug_weather_api(self, location):
        """Debug the wttr.in API response"""
        try:
            response = self.session.get(
                f"{self.server_url}/debug/weather", 
                params={'location': location}, 
                timeout=20
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check(self):
        """Check if the server is healthy"""
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

def main():
    """Example usage"""
    import sys
    
    # Create client
    client = TemperaturePlotSSEClient()
    
    # Check for debug mode
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        location = sys.argv[2] if len(sys.argv) > 2 else "New York"
        print(f"Debugging wttr.in API for: {location}")
        debug_result = client.debug_weather_api(location)
        print(json.dumps(debug_result, indent=2))
        return
    
    # Check server health
    print("Checking server health...")
    health = client.health_check()
    if health.get('status') != 'healthy':
        print(f"❌ Server health check failed: {health}")
        return
    print("✅ Server is healthy\n")
    
    # Get location from command line or use default
    if len(sys.argv) > 1:
        location = ' '.join(sys.argv[1:])
    else:
        location = input("Enter location (or press Enter for 'New York'): ").strip()
        if not location:
            location = "New York"
    
    print(f"\n{'='*50}")
    print("SSE Temperature Plot Demo")
    print(f"{'='*50}")
    
    # Custom callback for real-time updates
    def update_callback(event_type, data):
        if event_type == 'temperature_data':
            # Could save data or perform additional processing
            pass
    
    # Get temperature plot via SSE
    result = client.get_temperature_plot(location, days=5, callback=update_callback)
    
    print(f"\n{'='*50}")
    print("Final Result:")
    print(f"{'='*50}")
    
    if result and result.get('status') == 'completed':
        print(f"Location: {result.get('location', 'Unknown')}")
        print(f"Chart URL: {result.get('chart_url', 'Not available')}")
        
        temp_data = result.get('temperature_data', {})
        if temp_data.get('temperatures'):
            print(f"\nTemperature Summary:")
            temps = temp_data['temperatures']
            print(f"  Average: {sum(temps) // len(temps)}°C")
            print(f"  Min: {min(temps)}°C")
            print(f"  Max: {max(temps)}°C")
    else:
        print(f"❌ Failed to get temperature plot: {result}")

if __name__ == "__main__":
    main()