import os
import io
import csv
import zipfile
from typing import Optional, List, Dict
from flask import Flask, request, jsonify, send_from_directory, Response, send_file
from flask_cors import CORS
import numpy as np
from PIL import Image, ImageDraw
from PIL.ExifTags import TAGS
import flyr
from werkzeug.utils import secure_filename

# Setup upload and public folders
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
PUBLIC_FOLDER = os.path.join(BASE_DIR, 'public')

app = Flask(__name__, static_folder=PUBLIC_FOLDER, static_url_path='')
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Store processed image stats for CSV and batch downloads
processed_images_stats: Dict[str, dict] = {}

def celsius_to_fahrenheit(c):
    return c * 9 / 5 + 32

def render_palette_iron(thermogram, unit):
    # Render thermal image with iron palette
    return thermogram.render_pil(unit=unit, palette="inferno")

def extract_metadata_pil(filepath, flyr_thermogram, filename):
    # Extract EXIF metadata including emissivity and atmospheric temperature
    metadata = {}
    atmospheric_temp_c = 25.0  # default atmospheric temperature in Celsius
    try:
        img = Image.open(filepath)
        exifdata = img.getexif()
        metadata = {
            "component_name": filename,
            "file_size_kb": round(os.path.getsize(filepath) / 1024, 2),
            "width": img.width,
            "height": img.height,
            "emissivity": '0.95',
            "atmospheric_temp_c": atmospheric_temp_c,
        }
        for tag_id in exifdata:
            tag = TAGS.get(tag_id, tag_id)
            data = exifdata.get(tag_id)
            if isinstance(data, bytes):
                try:
                    data = data.decode()
                except:
                    data = str(data)
            if tag == 'AtmosphericTemperature':
                try:
                    atmospheric_temp_c = float(data)
                    metadata["atmospheric_temp_c"] = atmospheric_temp_c
                except:
                    pass
    except Exception:
        # Fallback metadata if EXIF reading fails
        metadata = {
            "component_name": filename,
            "file_size_kb": round(os.path.getsize(filepath) / 1024, 2),
            "width": flyr_thermogram.width,
            "height": flyr_thermogram.height,
            "emissivity": '0.95',
            "atmospheric_temp_c": atmospheric_temp_c,
        }
    return metadata

def analyze_and_render(flir_path: str, roi_coords: Optional[List[int]] = None, unit: str = "celsius") -> dict:
    # Analyze thermal image and ROI, render palette image with ROI rectangle
    x_min = y_min = x_max = y_max = 0
    try:
        thermogram = flyr.unpack(flir_path)
    except Exception as e:
        return {"error": f"Failed to unpack FLIR image: {e}"}

    thermal_data = thermogram.celsius if unit == 'celsius' else thermogram.fahrenheit
    unit_symbol = "°C" if unit == 'celsius' else "°F"

    height, width = thermal_data.shape

    max_temp_img = float(np.max(thermal_data))
    min_temp_img = float(np.min(thermal_data))
    avg_temp_img = float(np.mean(thermal_data))

    if roi_coords and len(roi_coords) == 4:
        x1, y1, x2, y2 = roi_coords
        # Clamp ROI coordinates within image bounds
        x1, x2 = max(0, min(x1, width - 1)), max(0, min(x2, width - 1))
        y1, y2 = max(0, min(y1, height - 1)), max(0, min(y2, height - 1))
        x_min, x_max = sorted([x1, x2])
        y_min, y_max = sorted([y1, y2])

        # Ignore zero-area ROI
        if x_max == x_min or y_max == y_min:
            x_min = y_min = x_max = y_max = 0

        roi = thermal_data[y_min:y_max + 1, x_min:x_max + 1]
        if roi.size == 0 and not (x_min == y_min == x_max == y_max == 0):
            return {"error": "Empty ROI selected."}

        max_temp_roi = float(np.max(roi)) if roi.size > 0 else None
        min_temp_roi = float(np.min(roi)) if roi.size > 0 else None
        avg_temp_roi = float(np.mean(roi)) if roi.size > 0 else None
    else:
        max_temp_roi = None
        min_temp_roi = None
        avg_temp_roi = None

    # Render palette image and draw ROI rectangle if valid
    paletted_img = render_palette_iron(thermogram, unit)
    draw = ImageDraw.Draw(paletted_img)
    if not (x_min == x_max == y_min == y_max == 0):
        draw.rectangle([x_min, y_min, x_max, y_max], outline="#CCCCCC", width=3)

    base_name, _ = os.path.splitext(os.path.basename(flir_path))
    output_filename = os.path.join(app.config['UPLOAD_FOLDER'], f'paletted_{base_name}.png')
    try:
        paletted_img.save(output_filename)
    except Exception as e:
        return {"error": f"Failed to save paletted image: {e}"}

    metadata = extract_metadata_pil(flir_path, thermogram, os.path.basename(flir_path))

    # Hotspot detection: ROI avg temp >= 2 * atmospheric temp
    atm_temp_c = metadata.get("atmospheric_temp_c", 25.0)
    atm_temp = celsius_to_fahrenheit(atm_temp_c) if unit == 'fahrenheit' else atm_temp_c

    hotspot_status = "Not Found"
    if avg_temp_roi is not None and avg_temp_roi >= 2 * atm_temp:
        hotspot_status = "Found"

    # Store stats for CSV and batch download
    processed_images_stats[os.path.basename(flir_path)] = {
        "filename": os.path.basename(flir_path),
        "metadata": metadata,
        "max_temp_img": max_temp_img,
        "min_temp_img": min_temp_img,
        "avg_temp_img": avg_temp_img,
        "max_temp_roi": max_temp_roi,
        "min_temp_roi": min_temp_roi,
        "avg_temp_roi": avg_temp_roi,
        "unit": unit_symbol,
        "paletted_image_url": f"/uploads/paletted_{base_name}.png",
        "roi_coords": [x_min, y_min, x_max, y_max] if (x_min != 0 or y_min != 0 or x_max != 0 or y_max != 0) else [],
        "hotspot_status": hotspot_status
    }

    return processed_images_stats[os.path.basename(flir_path)]

@app.route('/')
def index():
    # Serve frontend index.html
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Serve uploaded and paletted images
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload_image():
    # Upload and analyze single image (no validation gatekeeping)
    if 'image' not in request.files:
        return jsonify({"error": "No image part in the request"}), 400
    file = request.files['image']
    if not file or not file.filename:
        return jsonify({"error": "No selected image"}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    roi_coords_str = request.form.get('roi_coords')
    roi_coords = None
    if roi_coords_str:
        try:
            roi_coords = list(map(int, roi_coords_str.split(',')))
            if len(roi_coords) != 4:
                return jsonify({"error": "roi_coords must have exactly 4 integers"}), 400
        except ValueError:
            return jsonify({"error": "roi_coords must be integers separated by commas"}), 400

    unit = request.form.get('unit', 'celsius').lower()
    result = analyze_and_render(filepath, roi_coords, unit)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200

@app.route('/upload_batch', methods=['POST'])
def upload_batch():
    # Upload batch images (no validation gatekeeping)
    files = request.files.getlist('images')
    unit = request.form.get('unit', 'celsius').lower()

    if not files:
        return jsonify({"error": "No images uploaded"}), 400

    # Save all files
    for file in files:
        if not file or not file.filename:
            continue
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

    return jsonify({"message": f"{len(files)} images uploaded."}), 200

@app.route('/analyze_all_batch', methods=['POST'])
def analyze_all_batch():
    # Analyze all batch images with ROI and unit
    roi_coords_str = request.form.get('roi_coords')
    unit = request.form.get('unit', 'celsius').lower()
    files = request.files.getlist('images')

    if not files:
        return jsonify({"error": "No images uploaded"}), 400

    roi_coords = None
    if roi_coords_str:
        try:
            roi_coords = list(map(int, roi_coords_str.split(',')))
            if len(roi_coords) != 4:
                return jsonify({"error": "roi_coords must have exactly 4 integers"}), 400
        except ValueError:
            return jsonify({"error": "roi_coords must be integers separated by commas"}), 400

    results = []
    for file in files:
        if not file or not file.filename:
            continue
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        res = analyze_and_render(filepath, roi_coords, unit)
        results.append(res)

    if not results:
        return jsonify({"error": "No images analyzed"}), 400

    return jsonify(results), 200

@app.route('/download_csv')
def download_csv():
    # Generate CSV for processed images
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['name', 'max', 'avg', 'min', 'emissivity', 'hotspot_status'])
    for stat in processed_images_stats.values():
        meta = stat.get('metadata', {})
        cw.writerow([
            stat.get('filename', ''),
            f"{stat.get('max_temp_roi', 'N/A'):.2f}" if stat.get('max_temp_roi') is not None else 'N/A',
            f"{stat.get('avg_temp_roi', 'N/A'):.2f}" if stat.get('avg_temp_roi') is not None else 'N/A',
            f"{stat.get('min_temp_roi', 'N/A'):.2f}" if stat.get('min_temp_roi') is not None else 'N/A',
            meta.get('emissivity', '0.95'),
            stat.get('hotspot_status', 'Not Found')
        ])
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=thermal_roi_stats.csv"}
    )

@app.route('/download_paletted_zip')
def download_paletted_zip():
    # Create ZIP archive of paletted images for batch download
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'paletted_images.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for filename in processed_images_stats:
            paletted_name = f'paletted_{os.path.splitext(filename)[0]}.png'
            paletted_path = os.path.join(app.config['UPLOAD_FOLDER'], paletted_name)
            if os.path.exists(paletted_path):
                zipf.write(paletted_path, paletted_name)
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
