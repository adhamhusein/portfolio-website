#!/usr/bin/env python3
"""
Test script to debug upload issues for project 004
"""

import requests
import os
import tempfile
import csv

def create_test_csv(filename, rows=1000):
    """Create a test CSV file with specified number of rows."""
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['timestamp', 'latitude', 'longitude', 'altitude', 'speed'])
        
        for i in range(rows):
            writer.writerow([
                f'2024-01-01 12:00:{i:02d}',
                40.7128 + (i * 0.0001),  # Latitude
                -74.0060 + (i * 0.0001),  # Longitude
                100 + i,  # Altitude
                50 + (i % 20)  # Speed
            ])

def test_upload_config():
    """Test the upload configuration endpoint."""
    print("Testing upload configuration...")
    try:
        response = requests.get('http://localhost:5500/project/project_004_test_upload')
        if response.status_code == 200:
            config = response.json()
            print(f"✓ Upload configuration:")
            print(f"  - Max content length: {config['max_content_length_mb']:.1f} MB")
            print(f"  - Upload folder: {config['upload_folder']}")
            print(f"  - Allowed extensions: {config['upload_extensions']}")
        else:
            print(f"✗ Failed to get config: {response.status_code}")
    except Exception as e:
        print(f"✗ Error testing config: {e}")

def test_file_upload(file_path, file_type='position'):
    """Test uploading a file."""
    print(f"\nTesting upload of {file_path} ({file_type})...")
    
    file_size = os.path.getsize(file_path)
    print(f"File size: {file_size / (1024*1024):.2f} MB")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            data = {'file_type': file_type}
            
            response = requests.post(
                'http://localhost:5500/project/project_004_upload',
                files=files,
                data=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Upload successful: {result['filename']}")
                return True
            else:
                print(f"✗ Upload failed: {response.status_code}")
                try:
                    error = response.json()
                    print(f"  Error: {error.get('error', 'Unknown error')}")
                except:
                    print(f"  Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"✗ Upload error: {e}")
        return False

def main():
    """Main test function."""
    print("Project 004 Upload Test Script")
    print("=" * 40)
    
    # Test configuration
    test_upload_config()
    
    # Create test files of different sizes
    test_files = [
        ('small_test.csv', 100),      # ~5KB
        ('medium_test.csv', 10000),   # ~500KB
        ('large_test.csv', 100000),   # ~5MB
        ('xlarge_test.csv', 1000000), # ~50MB
    ]
    
    for filename, rows in test_files:
        print(f"\nCreating {filename} with {rows} rows...")
        create_test_csv(filename, rows)
        
        if test_file_upload(filename, 'position'):
            print(f"✓ {filename} upload test passed")
        else:
            print(f"✗ {filename} upload test failed")
        
        # Clean up test file
        os.remove(filename)
        print(f"Cleaned up {filename}")

if __name__ == '__main__':
    main() 