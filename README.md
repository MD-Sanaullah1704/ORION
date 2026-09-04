# ORION

## Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery

ORION is an offline-first geospatial intelligence prototype designed to help analysts search satellite imagery using natural-language queries and identify meaningful changes across multiple time periods.

The system combines semantic retrieval, satellite-image processing, change detection, geospatial metadata, and analyst review workflows into a single platform.

> **Project Status:** Active Prototype  
> **Problem Statement:** SIH26227  
> **Domain:** Defence / Geospatial Intelligence  
> **Primary Focus:** Satellite Image Retrieval and Multi-Temporal Change Analysis

---

## 1. Problem

Satellite imagery is continuously generated across different sensors, locations, and acquisition dates. Finding relevant imagery and identifying meaningful changes manually can be time-consuming.

Traditional image search systems often depend on:

- filenames
- metadata
- coordinates
- dates
- manually assigned labels

Similarly, basic image differencing can generate large numbers of false alarms caused by:

- seasonal variation
- atmospheric conditions
- image misalignment
- shadows
- haze
- illumination differences
- sensor/radiometric differences

ORION aims to address these problems by combining semantic retrieval with spatially coherent multi-temporal change analysis.

---

## 2. Objectives

ORION is designed around the following capabilities:

### Semantic Retrieval

Search satellite imagery using natural-language queries such as:

- `new construction`
- `road development`
- `water expansion`
- `cleared area`
- `large infrastructure`
- `changes near a settlement`

The retrieval system ranks relevant scenes based on their textual and metadata relevance.

### Multi-Temporal Change Detection

Compare satellite observations from different dates and identify spatially meaningful changes.

The current prototype performs:

- image loading
- radiometric normalization
- image registration
- pixel-level difference computation
- adaptive thresholding
- morphological filtering
- connected-component analysis
- object-level change region extraction

### False Alarm Reduction

ORION uses preprocessing and spatial filtering to reduce obvious noise and fragmented pixel-level detections.

Current processing includes:

- per-channel normalization
- image registration
- adaptive thresholds
- morphological opening
- morphological closing
- minimum connected-region filtering

Additional quality-aware and confidence-based filtering is planned.

### Analyst Review

Detected changes are intended to be presented with:

- before imagery
- after imagery
- detected change regions
- acquisition dates
- sensor information
- location
- affected area
- confidence
- processing history

Analysts can then review and confirm or reject detected changes.

---

## 3. Current Prototype

The current backend provides the foundation for the ORION processing pipeline.

### Implemented

- FastAPI backend
- Scene metadata storage
- Text-based scene retrieval
- Sensor filtering
- Change-type filtering
- Date filtering
- GeoTIFF inspection
- Raster metadata extraction
- Satellite image loading
- RGB normalization
- Image registration
- Adaptive change detection
- Morphological noise reduction
- Connected-component analysis
- Change-region statistics
- Change-mask generation

### Currently Being Developed

- Semantic image embeddings
- Multimodal retrieval
- Vector database/index
- Real geospatial coordinate handling
- Better change classification
- Quality/cloud/shadow masking
- Confidence estimation
- Analyst review workflow
- Incremental imagery ingestion
- Offline deployment
- Reproducible evaluation pipeline

---

## 4. Architecture

```text
                    ┌──────────────────────┐
                    │      Analyst         │
                    │ Natural Language     │
                    │ Search / Review      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    ORION Frontend    │
                    │ Map / Search / Review│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     FastAPI API      │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌────────────┐   ┌──────────────┐  ┌──────────────┐
       │ Retrieval  │   │   Change     │  │  Ingestion   │
       │  Service   │   │  Detection   │  │   Service    │
       └─────┬──────┘   └──────┬───────┘  └──────┬───────┘
             │                 │                 │
             ▼                 ▼                 ▼
       Scene Metadata     Change Masks      GeoTIFF / COG
       + Embeddings       + Regions         + Metadata
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Local / Offline     │
                    │  Data + Vector Index │
                    └──────────────────────┘

ORION/
│
├── backend/
│   ├── data/
│   │   └── scenes.json
│   │
│   ├── models/
│   │
│   ├── services/
│   │   ├── retrieval.py
│   │   ├── ingestion.py
│   │   └── change_detection.py
│   │
│   ├── main.py
│   └── requirements.txt
│
├── data/
│   ├── scenes/
│   │   └── prayagraj/
│   │       ├── before.tif
│   │       ├── after.tif
│   │       └── change_mask.png
│   │
│   ├── metadata/
│   │
│   └── thumbnails/
│
├── models/
│
├── frontend/
│
├── .gitignore
├── README.md
└── ...
6. Technology Stack
Backend
Python
FastAPI
Uvicorn
Geospatial Processing
Rasterio
PyProj
GeoTIFF / Cloud Optimized GeoTIFF
OpenCV
NumPy
Planned Retrieval Stack
Vision-language embeddings
Vector similarity search
Metadata filtering
Multimodal retrieval
Frontend
React
Vite
Leaflet / geospatial map interface
7. API

The current backend exposes the following endpoints.

Health Check
GET /health

Example response:

{
  "status": "healthy"
}
List Scenes
GET /scenes

Returns the currently indexed scene metadata.

Search Scenes
POST /search

Example request:

{
  "query": "construction",
  "sensor": "ALL",
  "change_type": "ALL"
}

Example response:

{
  "query": "construction",
  "count": 1,
  "results": [
    {
      "id": "ORION-001"
    }
  ]
}

The search endpoint currently supports:

natural-language keyword matching
sensor filtering
change-type filtering
start-date filtering
end-date filtering
relevance ranking

Semantic embedding-based retrieval will replace/extend the current keyword-based retrieval layer.
Technology Stack
Backend
Python
FastAPI
Uvicorn
Geospatial Processing
Rasterio
PyProj
GeoTIFF / Cloud Optimized GeoTIFF
OpenCV
NumPy
Planned Retrieval Stack
Vision-language embeddings
Vector similarity search
Metadata filtering
Multimodal retrieval
Frontend
React
Vite
Leaflet / geospatial map interface
7. API

The current backend exposes the following endpoints.

Health Check
GET /health

Example response:

{
  "status": "healthy"
}
List Scenes
GET /scenes

Returns the currently indexed scene metadata.

Search Scenes
POST /search

Example request:

{
  "query": "construction",
  "sensor": "ALL",
  "change_type": "ALL"
}

Example response:

{
  "query": "construction",
  "count": 1,
  "results": [
    {
      "id": "ORION-001"
    }
  ]
}

The search endpoint currently supports:

natural-language keyword matching
sensor filtering
change-type filtering
start-date filtering
end-date filtering
relevance ranking

Semantic embedding-based retrieval will replace/extend the current keyword-based retrieval layer.

8. Change Detection Pipeline

The current change detection pipeline follows these steps:

Before Image
      │
      ▼
Load RGB Bands
      │
      ▼
Per-Channel Normalization
      │
      ▼
Image Registration
      │
      ▼
After Image Alignment
      │
      ▼
Pixel-Level Difference
      │
      ▼
Adaptive Threshold
      │
      ▼
Morphological Filtering
      │
      ▼
Connected Components
      │
      ▼
Minimum Region Filtering
      │
      ▼
Change Regions
      │
      ▼
Change Mask + Statistics

Each detected region currently includes:

region ID
area in pixels
bounding box
centroid
mean change intensity
9. Example Dataset

The current prototype includes satellite imagery from Prayagraj, India.

The imagery is derived from the Copernicus Sentinel-2 mission and represents two observations of the Prayagraj area around the Maha Kumbh Mela period.

The project treats these files as satellite-derived observations while maintaining separate metadata because the downloaded TIFF files do not contain a usable geographic transform.

Important

The current image files are not committed to GitHub because of their large size.

They should be obtained separately and placed under:

data/scenes/prayagraj/

Expected files:

before.tif
after.tif
10. Running the Backend
1. Create / activate the virtual environment

Windows PowerShell:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& .venv\Scripts\Activate.ps1

You should see:

(.venv) PS C:\Users\Sanau\OneDrive\Desktop\ORION>
2. Install dependencies
pip install -r backend\requirements.txt
3. Start the API

From the ORION project root:

python -m uvicorn backend.main:app --reload

The backend should start locally.

API:

http://127.0.0.1:8000

Interactive API documentation:

http://127.0.0.1:8000/docs
11. Running Change Detection

The change detection service can process a pair of satellite images and generate a binary change mask.

Example input:

data/scenes/prayagraj/before.tif
data/scenes/prayagraj/after.tif

Example output:

data/scenes/prayagraj/change_mask.png

The output mask represents spatially coherent regions identified as potential change.

12. Current Change Detection Results

On the current Prayagraj image pair, the prototype progressed from a basic fixed threshold approach to an adaptive and region-filtered approach.

The current pipeline produces:

adaptive thresholding
morphological cleanup
connected change regions
region-level statistics

A representative run identified approximately 2.57% of pixels as changed after minimum-region filtering, with the largest detected region covering approximately 44,197 pixels.

These values are prototype-processing results and should not be interpreted as validated ground truth or operational intelligence.

13. Geospatial Data Handling

ORION is designed to support common satellite raster formats including:

GeoTIFF
Cloud Optimized GeoTIFF (COG)

The ingestion layer extracts metadata such as:

filename
raster dimensions
number of bands
CRS
pixel resolution
spatial bounds
data type
raster driver

The system is designed to preserve source metadata and processing provenance.

14. Offline-First Design

A major design goal of ORION is the ability to operate in environments where continuous internet access is unavailable or restricted.

The intended workflow is:

Online Staging
      │
      ├── Satellite Data
      ├── Models
      └── Required Libraries
             │
             ▼
      Local ORION System
             │
             ▼
       Offline Operation

After required imagery, models, indexes, and dependencies have been staged locally, the core analysis workflow should not depend on external APIs.

This architecture is intended to support controlled or air-gapped environments.

15. Data and Model Provenance

ORION is intended to maintain explicit provenance for:

Imagery
source
acquisition date
sensor
processing level
license
geographic coverage
Models
model name
source
version
license
weights checksum where applicable
Processing
preprocessing operations
registration method
detection parameters
model versions
processing timestamps

This information will support reproducibility and analyst auditability.

16. Evaluation Plan

The final prototype will be evaluated using measurable system-level metrics.

Retrieval
Precision@K
Recall@K
semantic query relevance
image-to-image retrieval accuracy
Change Detection
Precision
Recall
F1 score
IoU
false-positive rate

Because the problem prioritizes precision and false-alarm suppression, false positives will receive particular attention.

System Performance

The evaluation report will record:

indexed geographic area
number of scenes
number of tiles
index build time
index storage size
query latency
change-analysis latency
hardware configuration
17. Roadmap
Phase 1 — Backend Foundation
 FastAPI service
 Scene metadata
 Search endpoint
 Sensor filtering
 Change-type filtering
 Date filtering
Phase 2 — Geospatial Processing
 GeoTIFF inspection
 Raster loading
 Image normalization
 Image registration
 Adaptive change detection
 Morphological filtering
 Connected-component analysis
 Change-region statistics
Phase 3 — Intelligent Retrieval
 Image embeddings
 Text embeddings
 Vector index
 Multimodal search
 Image-to-image similarity
 Spatial and temporal filtering
Phase 4 — Robust Change Intelligence
 Cloud masking
 Shadow detection
 Atmospheric quality filtering
 Registration quality scoring
 Change classification
 Confidence estimation
 Earliest supported observation
Phase 5 — Analyst Workflow
 Ranked review queue
 Before/after comparison
 Change-region visualization
 Confirm / reject workflow
 Audit trail
 Processing provenance
Phase 6 — Scale and Deployment
 Incremental ingestion
 COG support
 Vector index scaling
 Offline deployment
 Reproducible evaluation
 Performance benchmarking
18. Limitations

This repository currently represents a prototype and should not be considered an operational intelligence system.

Current limitations include:

keyword-based retrieval instead of full semantic embeddings
limited imagery coverage
prototype-level change detection
no validated ground-truth benchmark yet
limited atmospheric/cloud/shadow handling
current Prayagraj TIFFs lack embedded georeferencing
no operational-grade confidence calibration
no production-scale vector index yet

Results should therefore be treated as experimental outputs.

19. Responsible Use

ORION is intended as a research and prototype system for satellite-image discovery and change analysis.

The system should not be used as the sole basis for operational decisions.

Human analyst review, source verification, uncertainty estimation, and appropriate authorization are required before acting on detected changes.

20. Team

Project: ORION
Problem Statement: SIH26227
Hackathon: Smart India Hackathon 2026

The project is being developed as a modular system covering:

frontend
backend/API
geospatial processing
machine learning
satellite imagery
retrieval/indexing
analyst workflow
evaluation
21. License and Data Attribution

Software licensing and third-party dataset licensing will be documented as the project incorporates external components.

Satellite imagery must be redistributed only according to the license and attribution requirements of its original provider.

For every external dataset or pretrained model, ORION will record:

Source:
Dataset / Model:
Version:
License:
URL:
Attribution:
Usage:
22. Disclaimer

ORION is an experimental research prototype developed for Smart India Hackathon 2026.

It is not a certified operational defence or intelligence system.

Detection results are subject to errors arising from image quality, registration, atmospheric conditions, sensor differences, temporal variation, and algorithmic limitations.
