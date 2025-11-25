import requests
import os

def verify_html_content(url, output_file):
    """Fetches HTML from a URL and saves it to a file."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        html_content = response.text
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"Successfully fetched HTML from {url} and saved to {output_file}")
        
        # Check if the key phrase is in the content
        if "Market Analysis Dashboard" in html_content:
            print("Verification PASSED: 'Market Analysis Dashboard' found in the HTML.")
        else:
            print("Verification FAILED: 'Market Analysis Dashboard' NOT found in the HTML.")
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching the URL: {e}")

if __name__ == "__main__":
    port = os.environ.get('DASH_PORT', os.environ.get('PORT', '8050'))
    app_url = f"http://127.0.0.1:{port}"
    output_html_file = "_last_root.html"
    verify_html_content(app_url, output_html_file)
