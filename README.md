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
