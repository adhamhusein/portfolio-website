from app.static.js.datasheet_processor_1 import VehicleDataProcessor
from app.static.js.datasheet_processor_2 import GeoJSONProcessor

class DatasheetProcessor:
    def __init__(self, input_file: str, output_file: str, datasheet_path: str = None):
        self.input_file = input_file
        self.output_file = output_file
        self.datasheet_path = datasheet_path
        self.vehicle_processor = VehicleDataProcessor(input_file, output_file)
        self.geojson_processor = GeoJSONProcessor(datasheet_path)
    
    def process_vehicle_data(self):
        return self.vehicle_processor.process()
    
    def convert_to_geojson(self, csv_path: str, geojson_path: str):
        self.geojson_processor.convert_csv_to_geojson(csv_path, geojson_path)
    
    def process_all(self, map_csv_path: str, geojson_output_path: str):
        vehicle_data = self.process_vehicle_data()
        self.convert_to_geojson(map_csv_path, geojson_output_path)
        return vehicle_data

def main():
    INPUT_FILE = "static/dataset/datasheet7.csv"
    OUTPUT_FILE = "static/dataset/datasheet13.csv"
    MAP_CSV_PATH = "static/dataset/map_dataset.csv"
    GEOJSON_OUTPUT_PATH = "static/dataset/map_dataset_2.geojson"
    
    try:
        processor = DatasheetProcessor(INPUT_FILE, OUTPUT_FILE, INPUT_FILE)
        processor.process_all(MAP_CSV_PATH, GEOJSON_OUTPUT_PATH)
        print("Processing completed successfully!")
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except Exception as e:
        print(f"An error occurred during processing: {e}")

if __name__ == "__main__":
    main() 