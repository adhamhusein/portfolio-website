import os
import uuid
import tempfile
from datetime import datetime
from app.static.js.datasheet_processor import DatasheetProcessor

class Project004Processor:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        self.session_id = str(uuid.uuid4())
        self.processed_files = {}
    
    def process_files(self, position_file_info, map_file_info):
        """
        Process uploaded files using datasheet processor with session-based unique filenames
        
        Args:
            position_file_info: Dict containing uploaded position file info
            map_file_info: Dict containing uploaded map file info
            
        Returns:
            Dict containing processed file paths and session info
        """
        try:
            # Generate unique session-based filenames
            session_prefix = f"session_{self.session_id}"
            
            # Input files (original uploaded files)
            position_input_path = os.path.join(self.upload_folder, position_file_info['filename'])
            map_input_path = os.path.join(self.upload_folder, map_file_info['filename'])
            
            # Output files (processed files with session prefix)
            processed_position_filename = f"{session_prefix}_processed_position.csv"
            processed_position_path = os.path.join(self.upload_folder, processed_position_filename)
            
            geojson_filename = f"{session_prefix}_map.geojson"
            geojson_path = os.path.join(self.upload_folder, geojson_filename)
            
            # Verify input files exist
            if not os.path.exists(position_input_path):
                raise FileNotFoundError(f"Position file not found: {position_input_path}")
            
            if not os.path.exists(map_input_path):
                raise FileNotFoundError(f"Map file not found: {map_input_path}")
            
            # Initialize datasheet processor
            processor = DatasheetProcessor(
                input_file=position_input_path,
                output_file=processed_position_path,
                datasheet_path=position_input_path  # Use position file as datasheet for road stats
            )
            
            # Process vehicle data
            print(f"Processing vehicle data for session {self.session_id}")
            vehicle_data = processor.process_vehicle_data()
            
            # Convert map to GeoJSON
            print(f"Converting map to GeoJSON for session {self.session_id}")
            processor.convert_to_geojson(map_input_path, geojson_path)
            
            # Store processed file information
            self.processed_files = {
                'session_id': self.session_id,
                'position_input': position_file_info,
                'map_input': map_file_info,
                'processed_position': {
                    'filename': processed_position_filename,
                    'path': processed_position_path,
                    'size': os.path.getsize(processed_position_path) if os.path.exists(processed_position_path) else 0
                },
                'geojson': {
                    'filename': geojson_filename,
                    'path': geojson_path,
                    'size': os.path.getsize(geojson_path) if os.path.exists(geojson_path) else 0
                },
                'processed_at': datetime.now().isoformat(),
                'vehicle_data_rows': len(vehicle_data) if vehicle_data is not None else 0
            }
            
            print(f"Processing completed successfully for session {self.session_id}")
            return self.processed_files
            
        except Exception as e:
            print(f"Error processing files for session {self.session_id}: {str(e)}")
            raise
    
    def get_processed_files(self):
        """Get information about processed files"""
        return self.processed_files
    
    def cleanup_session_files(self):
        """Clean up session-specific processed files"""
        try:
            if 'processed_position' in self.processed_files:
                pos_path = self.processed_files['processed_position']['path']
                if os.path.exists(pos_path):
                    os.remove(pos_path)
                    print(f"Cleaned up processed position file: {pos_path}")
            
            if 'geojson' in self.processed_files:
                geojson_path = self.processed_files['geojson']['path']
                if os.path.exists(geojson_path):
                    os.remove(geojson_path)
                    print(f"Cleaned up GeoJSON file: {geojson_path}")
                    
        except Exception as e:
            print(f"Error cleaning up session files: {str(e)}")

def create_session_processor(upload_folder):
    """Factory function to create a new session processor"""
    return Project004Processor(upload_folder) 