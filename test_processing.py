#!/usr/bin/env python3
"""
Test script to debug processing pipeline for project 004
"""

import os
import pandas as pd
import tempfile
from app.utils.project_004_processor import create_session_processor

def create_sample_position_csv(filename):
    """Create a sample position CSV file with required columns."""
    data = {
        'mobileid': [1, 1, 1, 2, 2, 2],
        'reporttime': ['2024-01-01 12:00:00', '2024-01-01 12:01:00', '2024-01-01 12:02:00',
                      '2024-01-01 12:00:00', '2024-01-01 12:01:00', '2024-01-01 12:02:00'],
        'mobiletypeid': [1, 1, 1, 1, 1, 1],
        'mobileactivityid': [1, 1, 8, 1, 1, 1],
        'mobilestatusid': [1, 1, 1, 1, 1, 1],
        'pos_lon': [106.8456, 106.8457, 106.8458, 106.8459, 106.8460, 106.8461],
        'pos_lat': [-6.2088, -6.2089, -6.2090, -6.2091, -6.2092, -6.2093],
        'pos_alt': [100, 101, 102, 103, 104, 105],
        'pos_speed': [10, 12, 0, 15, 18, 20],
        'pos_dir': [90, 95, 0, 85, 80, 75],
        'plm_payload': [50, 52, 0, 55, 58, 60],
        'plm_inc': [2, 3, 0, 1, 2, 3],
        'plm_status': [1, 1, 0, 1, 1, 1],
        'plm_speed': [10, 12, 0, 15, 18, 20]
    }
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Created sample position CSV: {filename}")
    return filename

def create_sample_map_csv(filename):
    """Create a sample map CSV file with required columns."""
    data = {
        'gid': [1, 2, 3],
        'objectname': ['Road1', 'Road2', 'Disposal1'],
        'geom_type': ['ROAD', 'ROAD', 'DISPOSAL'],
        'the_geom_text': [
            'LINESTRING(106.8456 -6.2088, 106.8457 -6.2089)',
            'LINESTRING(106.8458 -6.2090, 106.8459 -6.2091)',
            'POLYGON((106.8460 -6.2092, 106.8461 -6.2093, 106.8462 -6.2094, 106.8460 -6.2092))'
        ],
        'properties': [100.5, 150.2, 500.0]
    }
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Created sample map CSV: {filename}")
    return filename

def test_processing():
    """Test the processing pipeline with sample data."""
    print("=== Testing Processing Pipeline ===")
    
    # Create temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Create sample files
        position_file = os.path.join(temp_dir, "sample_position.csv")
        map_file = os.path.join(temp_dir, "sample_map.csv")
        
        create_sample_position_csv(position_file)
        create_sample_map_csv(map_file)
        
        # Create file info dictionaries
        position_file_info = {
            'filename': os.path.basename(position_file),
            'original_name': 'sample_position.csv',
            'file_path': position_file
        }
        
        map_file_info = {
            'filename': os.path.basename(map_file),
            'original_name': 'sample_map.csv',
            'file_path': map_file
        }
        
        # Copy files to uploads directory for processing
        uploads_dir = 'uploads'
        os.makedirs(uploads_dir, exist_ok=True)
        
        import shutil
        upload_position_path = os.path.join(uploads_dir, position_file_info['filename'])
        upload_map_path = os.path.join(uploads_dir, map_file_info['filename'])
        
        shutil.copy2(position_file, upload_position_path)
        shutil.copy2(map_file, upload_map_path)
        
        print(f"Copied files to uploads directory")
        print(f"Position file: {upload_position_path}")
        print(f"Map file: {upload_map_path}")
        
        try:
            # Test processing
            processor = create_session_processor(uploads_dir)
            print("Processor created successfully")
            
            result = processor.process_files(position_file_info, map_file_info)
            print("Processing completed successfully!")
            print(f"Session ID: {result['session_id']}")
            print(f"Processed files: {result['processed_files']}")
            
            # Check if output files exist
            processed_position_path = result['processed_position']['path']
            geojson_path = result['geojson']['path']
            
            if os.path.exists(processed_position_path):
                print(f"✓ Processed position file exists: {processed_position_path}")
                print(f"  Size: {os.path.getsize(processed_position_path)} bytes")
            else:
                print(f"✗ Processed position file missing: {processed_position_path}")
            
            if os.path.exists(geojson_path):
                print(f"✓ GeoJSON file exists: {geojson_path}")
                print(f"  Size: {os.path.getsize(geojson_path)} bytes")
            else:
                print(f"✗ GeoJSON file missing: {geojson_path}")
            
            return True
            
        except Exception as e:
            print(f"✗ Processing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_processing()
    if success:
        print("\n✓ Processing test passed!")
    else:
        print("\n✗ Processing test failed!") 