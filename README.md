# FLIR Thermal Inspector

FLIR Thermal Inspector is a web application that analyzes thermal images of FLIR cameras. It allows users to upload single or batch thermal images, select regions of interest (ROI), and visualize temperature statistics with an intuitive interface. The app renders thermal images using the "inferno" palette and detects hotspots based on ROI temperature relative to atmospheric temperature.

---

## Features

- **Single and Batch Image Upload:** Upload one or multiple FLIR thermal images for analysis.
- **ROI Selection:** Draw rectangular regions of interest on images to analyze specific areas.
- **Palette Rendering:** Thermal images are rendered with the popular "iron" palette.
- **Temperature Statistics:** View max, min, and average temperatures for the entire image and ROI.
- **Hotspot Detection:** Detect hotspots when the ROI average temperature exceeds twice the atmospheric temperature.
- **Download Options:** Download processed paletted images and CSV reports of temperature statistics.
- **Responsive UI:** Built with Bootstrap for a clean and responsive user experience.

---

## Project Structure

flir-thermal-inspector/
├── app.py # Flask backend server
├── requirements.txt # Python dependencies
├── public/ # Frontend files (HTML, CSS, JS)
│ └── index.html
├── uploads/ # Folder for uploaded and processed images (created at runtime)
├── README.md # This file

text

---

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- `pip` package manager

### Installation

1. **Clone the repository**

git clone https://github.com/<your-username>/flir-thermal-inspector.git
cd flir-thermal-inspector

text

2. **Create and activate a virtual environment**

python3 -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

text

3. **Install dependencies**

pip install -r requirements.txt

text

4. **Run the application**

export FLASK_APP=app.py
export FLASK_ENV=development
flask run

text

5. **Access the app**

Open your browser and navigate to `http://localhost:5000`

---

## Usage

- **Single Mode:**
  - Upload a FLIR thermal image.
  - Select the temperature unit (Celsius or Fahrenheit).
  - Draw a rectangular ROI on the image.
  - Click "Analyze ROI" to view temperature stats and paletted image.
  - Download paletted image or CSV report if needed.

- **Batch Mode:**
  - Upload multiple FLIR thermal images.
  - Select temperature unit.
  - Draw ROI on the preview image.
  - Use "Analyze Selected Image ROI" to analyze one image.
  - Use "Analyze All" to analyze all uploaded images with the same ROI.
  - Download paletted images ZIP and CSV report.

---

## Deployment

### Option 1: Deploy on Heroku

1. Create a `Procfile` with the following content:

web: gunicorn app:app

text

2. Commit and push your code to Heroku Git remote.

3. Heroku will automatically install dependencies and run your app.

### Option 2: Deploy with Docker

1. Build the Docker image:

docker build -t flir-thermal-inspector .

text

2. Run the container:

docker run -p 5000:5000 flir-thermal-inspector

text

3. Access the app at `http://localhost:5000`

### Option 3: Deploy on VPS or Cloud Server

- Use Gunicorn/uWSGI with Nginx reverse proxy.
- Set up a Python virtual environment.
- Configure systemd service for app management.

---

## Dependencies

- Flask
- Flask-CORS
- Flyr (for FLIR image unpacking)
- Pillow (PIL)
- NumPy
- Werkzeug

---
---

## Contact

For questions or support, please contact [Sharath J Rao](sharathrao.1948@gmail.com).

---

## Acknowledgments

- [Flyr](https://pypi.org/project/flyr/) for FLIR image handling.
- Bootstrap for frontend styling.
