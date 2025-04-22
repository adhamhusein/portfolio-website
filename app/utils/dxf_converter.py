# /app/utils/dxf_converter.py

from datetime import datetime
from flask import render_template
from werkzeug.utils import secure_filename
import ezdxf, os, json
import pandas as pd
from pyproj import Proj, transform
from shapely.geometry import Polygon, Point
import tempfile
import uuid
from flask import send_file
from shapely import wkt
from ezdxf.math import Matrix44

def mapping(geom):
    return geom.__geo_interface__

class DXFConverter:
    def __init__(self, file_path):
        self.file_path = file_path
        self.utm_proj = Proj(proj='utm', zone=50, datum='WGS84')
        self.wgs84_proj = Proj(proj='latlong', datum='WGS84')
        self.doc = ezdxf.readfile(self.file_path)
        self.polygon_list = []
        self.point_list = []

    def convert_dxf(self, date):
        for entity in self.doc.modelspace():
            if entity.dxftype() == 'POLYLINE':
                coordinates = []
                for vertex in entity.vertices:
                    lon, lat = transform(self.utm_proj, self.wgs84_proj, vertex.dxf.location.x, vertex.dxf.location.y)
                    coordinates.append([lon, lat])

                if coordinates[0] == coordinates[-1]:
                    polygon = Polygon(coordinates)
                    self.polygon_list.append(polygon)
                else:
                    continue
                
            elif entity.dxftype() == 'TEXT':
                lon, lat = transform(self.utm_proj, self.wgs84_proj, entity.dxf.insert.x, entity.dxf.insert.y)
                text = entity.dxf.text.replace("^J", "").replace("^", "").upper()
                self.point_list.append([lon, lat, text, date])

            elif entity.dxftype() == 'MTEXT':
                lon, lat = transform(self.utm_proj, self.wgs84_proj, entity.dxf.insert.x, entity.dxf.insert.y)
                text = entity.text.replace("^J", "").replace("^", "").strip().upper()
                self.point_list.append([lon, lat, text, date])

            elif entity.dxftype() == 'INSERT':
                insert_point = entity.dxf.insert
                transform_matrix = Matrix44().translate(insert_point.x, insert_point.y, insert_point.z)
                for attrib in entity.attribs:
                    local_point = attrib.dxf.insert
                    modelspace_point = transform_matrix.transform(local_point)
                    lon, lat = transform(self.utm_proj, self.wgs84_proj, modelspace_point.x, modelspace_point.y)
                    text = attrib.dxf.text.strip().upper().replace("^J", "").replace("^", "").replace("\\N", "").replace("\\", "")
                    self.point_list.append([lon, lat, text, date])
                
    def filter_polygons(self):
        filtered_polygon_list = []
        df_polygon = pd.DataFrame(self.polygon_list, columns=["Geometry"])
        for i, row_i in df_polygon.iterrows():
            is_inside = False
            for j, row_j in df_polygon.iterrows():
                if i != j and row_i["Geometry"].within(row_j["Geometry"]):
                    is_inside = True
                    break
            if not is_inside:
                filtered_polygon_list.append(row_i["Geometry"])
        return filtered_polygon_list

    def process_points(self, filtered_polygon_list, date):
        df_point = pd.DataFrame(self.point_list, columns=["lon", "lat", "text", "date"])
        results = []
        for polygon in filtered_polygon_list:
            texts_in_poly = []
            for _, row_point in df_point.iterrows():
                point = Point(row_point["lon"], row_point["lat"])
                if point.within(polygon) or point.touches(polygon):
                    texts_in_poly.append(row_point["text"])
            combined_text = " ".join(sorted(set(texts_in_poly))).strip() if texts_in_poly else "NO BLAST CODE"
            
            results.append({
                "lon": polygon.centroid.x,
                "lat": polygon.centroid.y,
                "text": "NO BLAST CODE" if not combined_text.strip() else combined_text,
                "polygon": polygon
            })
        return results

def handle_project_001(request, upload_folder):
    result_text = None
    if request.method == 'POST':
        file = request.files['dxf_file']
        date_str = request.form['dxf_date']
        date = datetime.strptime(date_str, "%Y-%m-%d")
        filename = secure_filename(file.filename)
        dxf_path = os.path.join(upload_folder, filename)
        file.save(dxf_path)

        # Convert
        converter = DXFConverter(dxf_path)
        converter.convert_dxf(date)

        result_lines = []
        # === TEXT INSERT ===
        if converter.point_list:
            result_lines.append("--=== TEXTS ===--")
            result_lines.append("CINGKLANGKONGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG")
            result_lines.append("INSERT INTO ref_blastid (point_date, point_lon, point_lat, point_text, polygon_wkt, updated_at)")
            result_lines.append("VALUES")

            text_values = []
            processed_points = converter.process_points(converter.filter_polygons(), date)  # Pass date here
            for point in processed_points:
                point_date = date.strftime("%Y-%m-%d")  # Use the date inserted by the user in yyyy-mm-dd format
                point_lon = point["lon"]
                point_lat = point["lat"]
                point_text = point["text"]
                polygon_wkt = point["polygon"]
                text_values.append(f"('{point_date}', {point_lon}, {point_lat}, '{point_text}', '{polygon_wkt}', GETDATE())")

            result_lines.append(",\n".join(text_values) + ";")
            result_lines.append("")
        result_text = "\n".join(result_lines)

        # === PREPARE GEOJSON ===
        features = []

        # Points inside filtered polygons, directly using the user input date
        for point in converter.process_points(converter.filter_polygons(), date):  # Pass date here
            lon = point["lon"]
            lat = point["lat"]
            text = point["text"]
            # Directly use the user input date for each point
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "text": text,
                    "date": str(date)  # Directly use the date from user input
                }
            })

        # Polygons
        for poly in converter.filter_polygons():
            geojson_geom = mapping(poly)
            features.append({
                "type": "Feature",
                "geometry": geojson_geom,
                "properties": {}
            })

        # Save to temp file (add all features)
        geojson_data = {
            "type": "FeatureCollection",
            "features": features  # Store all features in the list
        }

        temp_geojson_path = os.path.join(tempfile.gettempdir(), f"{filename.split('.')[0]}_geojson.geojson")
        with open(temp_geojson_path, 'w') as f:
            json.dump(geojson_data, f)

        return render_template(
            'project_001.html',
            result=result_text,
            geojson_download=temp_geojson_path
        )
    return render_template('project_001.html')
