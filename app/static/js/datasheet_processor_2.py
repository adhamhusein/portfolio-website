import pandas as pd
import json
import numpy as np
from typing import Optional

class GeoJSONProcessor:
    def __init__(self, datasheet_path: Optional[str] = None):
        self.datasheet_path = datasheet_path
        self.road_stats = None
        if datasheet_path:
            self.road_stats = self._aggregate_road_properties(datasheet_path)
    
    def _linestring_wkt_to_coords(self, wkt: str) -> list:
        # Convert WKT LINESTRING to GeoJSON coordinates
        wkt = wkt.replace('LINESTRING(', '').replace(')', '')
        return [list(map(float, point.split())) for point in wkt.split(',')]

    def _polygon_wkt_to_coords(self, wkt: str) -> list:
        # Convert WKT POLYGON to GeoJSON coordinates
        wkt = wkt.replace('POLYGON((', '').replace('))', '')
        coords = [list(map(float, point.split())) for point in wkt.split(',')]
        return [coords]  # GeoJSON expects a list of linear rings

    def _aggregate_road_properties(self, datasheet_path: str) -> pd.DataFrame:
        # Aggregate average speed, road grade, and altitude from datasheet grouped by pos_name
        columns = ['pos_name', 'pos_speed', 'plm_inc', 'pos_alt']
        df = pd.read_csv(datasheet_path, usecols=columns)
        df = df.dropna(subset=['pos_name'])
        
        avg_speed = df.groupby('pos_name')['pos_speed'].mean()
        
        df_nonzero = df[df['plm_inc'] != 0].copy()
        df_nonzero['plm_inc'] = df_nonzero['plm_inc'].abs()
        grade = df_nonzero.groupby('pos_name')['plm_inc'].mean()
        
        altitude = df[df['pos_alt'] != 0].groupby('pos_name')['pos_alt'].mean()
        zero_speed_count = df[df['pos_speed'] < 1].groupby('pos_name').size()
        
        return pd.DataFrame({
            'avg_speed': avg_speed,
            'road_grade': grade,
            'altitude': altitude,
            'zero_speed': zero_speed_count
        })

    def convert_csv_to_geojson(self, csv_path: str, geojson_path: str) -> None:
        # Convert a CSV with WKT geometries to a GeoJSON file, optionally merging in road statistics
        df = pd.read_csv(csv_path)
        features = []
        for _, row in df.iterrows():
            wkt = row['the_geom_text']
            geom_type = row['geom_type'].upper()
            # Geometry conversion
            if wkt.startswith('LINESTRING') or geom_type == 'ROAD':
                geometry = {
                    "type": "LineString",
                    "coordinates": self._linestring_wkt_to_coords(wkt)
                }
            elif wkt.startswith('POLYGON') or geom_type == 'DISPOSAL':
                geometry = {
                    "type": "Polygon",
                    "coordinates": self._polygon_wkt_to_coords(wkt)
                }
            else:
                continue  # Skip unknown geometry types
            # Build properties dictionary
            prop_key = 'length' if geom_type == 'ROAD' else 'area'
            properties = {
                "gid": row['gid'],
                "objectname": row['objectname'],
                "geom_type": row['geom_type'],
                prop_key: row['properties']
            }
            # Add aggregated statistics as top-level keys if available
            if self.road_stats is not None and row['objectname'] in self.road_stats.index:
                stats = self.road_stats.loc[row['objectname']].dropna().to_dict()
                if 'avg_speed' in stats:
                    properties['avg_speed'] = round(stats['avg_speed'], 2)
                if 'road_grade' in stats:
                    properties['grade'] = round(stats['road_grade'], 2)
                if 'altitude' in stats:
                    properties['altitude'] = round(stats['altitude'], 2)
                if 'zero_speed' in stats:
                    properties['zero_speed'] = int(stats['zero_speed'])
            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": properties
            }
            features.append(feature)
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        with open(geojson_path, 'w') as f:
            json.dump(geojson, f, indent=2)
        print(f'GeoJSON file created: {geojson_path}')

# Backward compatibility functions
def linestring_wkt_to_coords(wkt: str) -> list:
    processor = GeoJSONProcessor()
    return processor._linestring_wkt_to_coords(wkt)

def polygon_wkt_to_coords(wkt: str) -> list:
    processor = GeoJSONProcessor()
    return processor._polygon_wkt_to_coords(wkt)

def aggregate_road_properties(datasheet_path: str) -> pd.DataFrame:
    processor = GeoJSONProcessor()
    return processor._aggregate_road_properties(datasheet_path)

def csv_to_geojson(csv_path: str, geojson_path: str, datasheet_path: Optional[str] = None) -> None:
    processor = GeoJSONProcessor(datasheet_path)
    processor.convert_csv_to_geojson(csv_path, geojson_path)
