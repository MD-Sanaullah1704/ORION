import { useEffect, useMemo, useState } from "react";
import MapView from "./MapView";

const API_BASE_URL = "http://127.0.0.1:8000";

/* ============================================================
   HELPERS
============================================================ */

function extractTileId(tileId) {
  if (typeof tileId === "number") {
    return tileId;
  }

  if (typeof tileId !== "string") {
    return null;
  }

  const tileMatch =
    tileId.match(/tile_(\d+)_x/i);

  if (tileMatch) {
    return Number(tileMatch[1]);
  }

  const eventMatch =
    tileId.match(
      /(?:event|jewar_event)[_-]?(\d+)/i
    );

  if (eventMatch) {
    return Number(eventMatch[1]);
  }

  const numericMatch =
    tileId.match(/(\d+)$/);

  if (numericMatch) {
    return Number(
      numericMatch[1]
    );
  }

  return null;
}

function formatPercentage(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return `${number.toFixed(2)}%`;
}

function formatScore(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toFixed(3);
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  return String(value).slice(0, 10);
}

function isJewarEvent(event, scene) {
  const dataset =
    event?.dataset ??
    scene?.dataset ??
    scene?.datasetId ??
    "";

  const sceneId =
    event?.scene_id ??
    scene?.sceneId ??
    "";

  return (
    dataset ===
      "jewar_airport_best" ||
    dataset ===
      "jewar_airport" ||
    sceneId ===
      "jewar_airport"
  );
}

function getDatasetLabel(
  event,
  scene
) {
  if (
    isJewarEvent(
      event,
      scene
    )
  ) {
    return "JEWAR AIRPORT";
  }

  const dataset =
    event?.dataset ??
    scene?.dataset ??
    scene?.sceneId ??
    "PRAYAGRAJ";

  return String(
    dataset
  )
    .replaceAll("_", " ")
    .toUpperCase();
}

function getLocationLabel(
  event,
  scene
) {
  if (
    event?.location
  ) {
    return event.location;
  }

  if (
    scene?.location
  ) {
    return scene.location;
  }

  if (
    isJewarEvent(
      event,
      scene
    )
  ) {
    return "Noida International Airport area, Jewar, Uttar Pradesh";
  }

  return "Prayagraj, Uttar Pradesh";
}

function getSensorLabel(
  event,
  scene
) {
  return (
    event?.sensor ??
    event?.before?.sensor ??
    event?.after?.sensor ??
    scene?.sensor ??
    (isJewarEvent(
      event,
      scene
    )
      ? "Copernicus Sentinel-2"
      : "Satellite imagery")
  );
}

function getProductLabel(
  event,
  scene
) {
  return (
    event?.product ??
    event?.before?.product ??
    event?.after?.product ??
    scene?.product ??
    (isJewarEvent(
      event,
      scene
    )
      ? "Sentinel-2 Level-2A Surface Reflectance"
      : "RGB satellite imagery")
  );
}

function getResolutionLabel(
  event,
  scene
) {
  if (
    isJewarEvent(
      event,
      scene
    )
  ) {
    return "10 m";
  }

  return (
    event?.resolution ??
    scene?.resolution ??
    "256 × 256 tile"
  );
}

function getMGRSLabel(event) {
  return (
    event?.mgrs_tile ??
    event?.mgrsTile ??
    "—"
  );
}

function getCRSLabel(event) {
  return (
    event?.source_crs ??
    event?.sourceCRS ??
    "—"
  );
}

function getPixelSizeLabel(event) {
  const value =
    Number(
      event?.pixel_size_m
    );

  if (
    Number.isFinite(value)
  ) {
    return `${value} m`;
  }

  return "—";
}

function getChangeMaskUrl(
  evidence
) {
  return (
    evidence?.change_mask?.url ??
    evidence?.changeMask?.url ??
    ""
  );
}

function getEvidenceUrl(
  evidence,
  key
) {
  return (
    evidence?.[key]?.url ??
    ""
  );
}

/* ============================================================
   SCENE DETAIL
============================================================ */

function SceneDetail({
  scene,
  onBack,
}) {
  const [evidence, setEvidence] =
    useState(null);

  const [eventData, setEventData] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [maskOpacity, setMaskOpacity] =
    useState(0.65);

  const [showMask, setShowMask] =
    useState(true);

  const [viewMode, setViewMode] =
    useState("change");

  const numericTileId =
    useMemo(
      () =>
        extractTileId(
          scene?.tileId
        ),
      [scene?.tileId]
    );

  /* ============================================================
     DATASET MODE
  ============================================================ */

  const jewarMode =
    useMemo(
      () =>
        isJewarEvent(
          eventData,
          scene
        ),
      [eventData, scene]
    );

  const datasetLabel =
    useMemo(
      () =>
        getDatasetLabel(
          eventData,
          scene
        ),
      [eventData, scene]
    );

  const locationLabel =
    useMemo(
      () =>
        getLocationLabel(
          eventData,
          scene
        ),
      [eventData, scene]
    );

  const sensorLabel =
    useMemo(
      () =>
        getSensorLabel(
          eventData,
          scene
        ),
      [eventData, scene]
    );

  const productLabel =
    useMemo(
      () =>
        getProductLabel(
          eventData,
          scene
        ),
      [eventData, scene]
    );

  const resolutionLabel =
    useMemo(
      () =>
        getResolutionLabel(
          eventData,
          scene
        ),
      [eventData, scene]
    );

  /* ============================================================
     LOAD EVENT + EVIDENCE
  ============================================================ */

  useEffect(() => {
    let cancelled = false;

    async function loadEvidence() {
      if (
        numericTileId === null
      ) {
        setEvidence(null);
        setEventData(null);
        setError(
          "Unable to determine the numeric event ID."
        );
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError("");

        /*
         * Load the complete change event.
         *
         * This contains:
         * - dataset
         * - dates
         * - change statistics
         * - priority
         * - confidence
         * - classification
         * - geospatial information
         */

        const eventResponse =
          await fetch(
            `${API_BASE_URL}/change-events/${numericTileId}`
          );

        if (
          !eventResponse.ok
        ) {
          const errorText =
            await eventResponse.text();

          throw new Error(
            `Event API HTTP ${eventResponse.status}: ${errorText}`
          );
        }

        const event =
          await eventResponse.json();

        /*
         * Load evidence separately.
         */

        const evidenceResponse =
          await fetch(
            `${API_BASE_URL}/change-events/${numericTileId}/evidence`
          );

        if (
          !evidenceResponse.ok
        ) {
          const errorText =
            await evidenceResponse.text();

          throw new Error(
            `Evidence API HTTP ${evidenceResponse.status}: ${errorText}`
          );
        }

        const evidenceData =
          await evidenceResponse.json();

        if (!cancelled) {
          setEventData(
            event
          );

          setEvidence(
            evidenceData
          );
        }
      } catch (requestError) {
        console.error(
          "ORION scene detail loading failed:",
          requestError
        );

        if (!cancelled) {
          setEvidence(null);
          setEventData(null);

          setError(
            "Unable to load real satellite evidence."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadEvidence();

    return () => {
      cancelled = true;
    };
  }, [numericTileId]);

  /* ============================================================
     IMAGE URLS
  ============================================================ */

  const beforeImageUrl =
    useMemo(() => {
      const url =
        getEvidenceUrl(
          evidence,
          "before"
        );

      if (!url) {
        return "";
      }

      return `${API_BASE_URL}${url}`;
    }, [evidence]);

  const afterImageUrl =
    useMemo(() => {
      const url =
        getEvidenceUrl(
          evidence,
          "after"
        );

      if (!url) {
        return "";
      }

      return `${API_BASE_URL}${url}`;
    }, [evidence]);

  const maskImageUrl =
    useMemo(() => {
      const url =
        getChangeMaskUrl(
          evidence
        );

      if (!url) {
        return "";
      }

      return `${API_BASE_URL}${url}?v=7`;
    }, [evidence]);

  /* ============================================================
     MAP DATA
  ============================================================ */

  const mapScene =
    useMemo(
      () => ({
        ...(scene || {}),

        sceneId:
          eventData?.scene_id ??
          scene?.sceneId ??
          "prayagraj",

        dataset:
          eventData?.dataset ??
          scene?.dataset ??
          "prayagraj",

        location:
          eventData?.location ??
          scene?.location ??
          "",

        geospatial:
          eventData?.geospatial ??
          null,

        source_crs:
          eventData?.source_crs ??
          null,

        pixel_size_m:
          eventData?.pixel_size_m ??
          null,

        mgrs_tile:
          eventData?.mgrs_tile ??
          null,

        x:
          eventData?.x ??
          scene?.x ??
          null,

        y:
          eventData?.y ??
          scene?.y ??
          null,
      }),
      [
        scene,
        eventData,
      ]
    );

  const geospatialAvailable =
    eventData?.geospatial
      ?.status ===
    "available";

  /* ============================================================
     TEMPORAL INFORMATION
  ============================================================ */

  const beforeDate =
    evidence?.before?.date ??
    eventData?.before_date ??
    eventData?.before?.date ??
    scene?.beforeDate ??
    "—";

  const afterDate =
    evidence?.after?.date ??
    eventData?.after_date ??
    eventData?.after?.date ??
    scene?.date ??
    "—";

  const changeType =
    evidence?.dominant_change_type ??
    eventData?.dominant_change_type ??
    "—";

  const changePercentage =
    evidence?.change_percentage ??
    eventData?.change_percentage ??
    null;

  const severity =
    evidence?.severity ??
    evidence?.severity_score ??
    eventData?.severity_score ??
    eventData?.severity ??
    null;

  const evidenceScore =
    eventData?.evidence_score ??
    evidence?.evidence_score ??
    null;

  const classificationScore =
    evidence?.classification_score ??
    eventData?.classification_score ??
    null;

  const priority =
    evidence?.priority ??
    eventData?.priority ??
    "—";

  const confidence =
    evidence?.evidence_confidence ??
    eventData?.evidence_confidence ??
    "—";

  const falseAlarmRisk =
    evidence?.false_alarm_risk ??
    eventData?.false_alarm_risk ??
    "—";

  const changeRegions =
    eventData?.change_regions ??
    evidence?.change_regions ??
    eventData?.regions?.length ??
    0;

  const changedPixels =
    eventData?.changed_pixels ??
    evidence?.changed_pixels ??
    0;

  /* ============================================================
     MASK
  ============================================================ */

  function toggleMask() {
    setShowMask(
      (currentValue) =>
        !currentValue
    );
  }

  function handleOpacityChange(
    event
  ) {
    setMaskOpacity(
      Number(
        event.target.value
      )
    );
  }

  /* ============================================================
     RENDER
  ============================================================ */

  return (
    <section className="scene-detail">

      {/* ======================================================
          BACK
      ====================================================== */}

      <div className="scene-detail-back">
        <button
          type="button"
          className="scene-back-button"
          onClick={onBack}
        >
          ← BACK TO RESULTS
        </button>
      </div>

      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="scene-detail-header">

        <div>

          <span className="section-label">
            03 / SCENE INTELLIGENCE
          </span>

          <h3>
            {jewarMode
              ? `JEWAR EVENT ${numericTileId}`
              : scene?.tileId ||
                `EVENT ${numericTileId}`}
          </h3>

          <div className="scene-header-coordinates">

            <span>
              DATASET:{" "}
              {datasetLabel}
            </span>

            <span>
              LOCATION:{" "}
              {locationLabel}
            </span>

            <span>
              SENSOR:{" "}
              {sensorLabel}
            </span>

          </div>

        </div>

        <div
          className={
            loading
              ? "evidence-status loading"
              : evidence
              ? "evidence-status ready"
              : "evidence-status error"
          }
        >

          <span className="status-dot"></span>

          {loading
            ? "LOADING EVIDENCE"
            : evidence
            ? "EVIDENCE LOADED"
            : "EVIDENCE UNAVAILABLE"}

        </div>

      </div>

      {/* ======================================================
          ERROR
      ====================================================== */}

      {error && (
        <div className="scene-error">
          {error}
        </div>
      )}

      {/* ======================================================
          DATASET INFORMATION
      ====================================================== */}

      <section className="scene-section">

        <div className="scene-section-heading">

          <div>

            <span className="section-label">
              DATASET CONTEXT
            </span>

            <h4>
              {jewarMode
                ? "SENTINEL-2 TEMPORAL AOI"
                : "SCENE INFORMATION"}
            </h4>

          </div>

        </div>

        <div
          className="evidence-grid"
        >

          <article className="evidence-card">

            <span className="evidence-label">
              LOCATION
            </span>

            <strong>
              {locationLabel}
            </strong>

            <p>
              Dataset
            </p>

            <small>
              {datasetLabel}
            </small>

          </article>

          <article className="evidence-card">

            <span className="evidence-label">
              SENSOR
            </span>

            <strong>
              {sensorLabel}
            </strong>

            <p>
              Product
            </p>

            <small>
              {productLabel}
            </small>

          </article>

          <article className="evidence-card">

            <span className="evidence-label">
              SPATIAL RESOLUTION
            </span>

            <strong>
              {resolutionLabel}
            </strong>

            <p>
              Pixel size
            </p>

            <small>
              {getPixelSizeLabel(
                eventData
              )}
            </small>

          </article>

          <article className="evidence-card">

            <span className="evidence-label">
              REFERENCE GRID
            </span>

            <strong>
              {getMGRSLabel(
                eventData
              )}
            </strong>

            <p>
              Source CRS
            </p>

            <small>
              {getCRSLabel(
                eventData
              )}
            </small>

          </article>

        </div>

      </section>

      {/* ======================================================
          TEMPORAL COMPARISON
      ====================================================== */}

      <section className="scene-section">

        <div className="scene-section-heading">

          <div>

            <span className="section-label">
              TEMPORAL COMPARISON
            </span>

            <h4>
              BEFORE / AFTER
            </h4>

          </div>

          <div className="temporal-date-range">

            <strong>
              {formatDate(
                beforeDate
              )}
            </strong>

            <span>
              →
            </span>

            <strong>
              {formatDate(
                afterDate
              )}
            </strong>

          </div>

        </div>

        <div className="temporal-grid">

          {/* BEFORE */}

          <article className="temporal-panel">

            <div className="temporal-panel-header">

              <div>

                <span>
                  BEFORE
                </span>

                <strong>
                  {formatDate(
                    beforeDate
                  )}
                </strong>

              </div>

              <span className="temporal-source">
                {jewarMode
                  ? "SENTINEL-2 B04"
                  : "BEFORE.TIF"}
              </span>

            </div>

            <div className="temporal-image">

              {beforeImageUrl ? (
                <img
                  src={
                    beforeImageUrl
                  }
                  alt={`Before satellite imagery ${numericTileId}`}
                  className="real-satellite-image"
                />
              ) : (
                <div className="image-placeholder">
                  BEFORE IMAGE
                  <br />
                  UNAVAILABLE
                </div>
              )}

            </div>

          </article>

          {/* AFTER */}

          <article className="temporal-panel">

            <div className="temporal-panel-header">

              <div>

                <span>
                  AFTER
                </span>

                <strong>
                  {formatDate(
                    afterDate
                  )}
                </strong>

              </div>

              <span className="temporal-source">
                {jewarMode
                  ? "SENTINEL-2 B04"
                  : "AFTER.TIF"}
              </span>

            </div>

            <div className="temporal-image">

              {afterImageUrl ? (
                <img
                  src={
                    afterImageUrl
                  }
                  alt={`After satellite imagery ${numericTileId}`}
                  className="real-satellite-image"
                />
              ) : (
                <div className="image-placeholder">
                  AFTER IMAGE
                  <br />
                  UNAVAILABLE
                </div>
              )}

            </div>

          </article>

        </div>

      </section>

      {/* ======================================================
          CHANGE DETECTION
      ====================================================== */}

      <section className="scene-section">

        <div className="scene-section-heading">

          <div>

            <span className="section-label">
              CHANGE DETECTION
            </span>

            <h4>
              TEMPORAL VIEWER
            </h4>

          </div>

          {viewMode ===
            "change" && (
            <button
              type="button"
              className="mask-toggle"
              onClick={
                toggleMask
              }
            >
              {showMask
                ? "HIDE MASK"
                : "SHOW MASK"}
            </button>
          )}

        </div>

        {/* VIEW SELECTOR */}

        <div
          className="scene-view-selector"
          role="tablist"
          aria-label="Temporal comparison view"
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(3, minmax(0, 1fr))",
            gap:
              "8px",
            marginBottom:
              "14px",
          }}
        >

          <button
            type="button"
            role="tab"
            aria-selected={
              viewMode ===
              "before"
            }
            onClick={() =>
              setViewMode(
                "before"
              )
            }
            style={{
              padding:
                "12px 16px",
              border:
                "1px solid #d1d5db",
              background:
                viewMode ===
                "before"
                  ? "#111827"
                  : "#ffffff",
              color:
                viewMode ===
                "before"
                  ? "#ffffff"
                  : "#111827",
              fontWeight:
                800,
              fontSize:
                "11px",
              letterSpacing:
                "0.08em",
              cursor:
                "pointer",
            }}
          >
            BEFORE
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={
              viewMode ===
              "after"
            }
            onClick={() =>
              setViewMode(
                "after"
              )
            }
            style={{
              padding:
                "12px 16px",
              border:
                "1px solid #d1d5db",
              background:
                viewMode ===
                "after"
                  ? "#111827"
                  : "#ffffff",
              color:
                viewMode ===
                "after"
                  ? "#ffffff"
                  : "#111827",
              fontWeight:
                800,
              fontSize:
                "11px",
              letterSpacing:
                "0.08em",
              cursor:
                "pointer",
            }}
          >
            AFTER
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={
              viewMode ===
              "change"
            }
            onClick={() =>
              setViewMode(
                "change"
              )
            }
            style={{
              padding:
                "12px 16px",
              border:
                "1px solid #d1d5db",
              background:
                viewMode ===
                "change"
                  ? "#111827"
                  : "#ffffff",
              color:
                viewMode ===
                "change"
                  ? "#ffffff"
                  : "#111827",
              fontWeight:
                800,
              fontSize:
                "11px",
              letterSpacing:
                "0.08em",
              cursor:
                "pointer",
            }}
          >
            CHANGE + MASK
          </button>

        </div>

        {/* LARGE VIEWER */}

        <div
          className="change-visual"
          style={{
            position:
              "relative",
            overflow:
              "hidden",
          }}
        >

          {/* BEFORE */}

          {viewMode ===
            "before" && (
            beforeImageUrl ? (
              <img
                src={
                  beforeImageUrl
                }
                alt={`Before satellite imagery ${numericTileId}`}
                className="change-base-image"
                style={{
                  width:
                    "100%",
                  height:
                    "100%",
                  objectFit:
                    "contain",
                  display:
                    "block",
                }}
              />
            ) : (
              <div className="image-placeholder">
                BEFORE IMAGE
                <br />
                UNAVAILABLE
              </div>
            )
          )}

          {/* AFTER */}

          {viewMode ===
            "after" && (
            afterImageUrl ? (
              <img
                src={
                  afterImageUrl
                }
                alt={`After satellite imagery ${numericTileId}`}
                className="change-base-image"
                style={{
                  width:
                    "100%",
                  height:
                    "100%",
                  objectFit:
                    "contain",
                  display:
                    "block",
                }}
              />
            ) : (
              <div className="image-placeholder">
                AFTER IMAGE
                <br />
                UNAVAILABLE
              </div>
            )
          )}

          {/* AFTER + MASK */}

          {viewMode ===
            "change" && (
            <>
              {afterImageUrl ? (
                <img
                  src={
                    afterImageUrl
                  }
                  alt={`After imagery used for change analysis ${numericTileId}`}
                  className="change-base-image"
                  style={{
                    position:
                      "absolute",
                    inset:
                      0,
                    width:
                      "100%",
                    height:
                      "100%",
                    objectFit:
                      "contain",
                    display:
                      "block",
                    zIndex:
                      1,
                  }}
                />
              ) : (
                <div className="image-placeholder">
                  AFTER IMAGE
                  <br />
                  UNAVAILABLE
                </div>
              )}

              {showMask &&
                maskImageUrl &&
                afterImageUrl && (
                  <img
                    src={
                      maskImageUrl
                    }
                    alt={`Detected change mask ${numericTileId}`}
                    className="change-mask-image"
                    style={{
                      position:
                        "absolute",
                      inset:
                        0,
                      width:
                        "100%",
                      height:
                        "100%",
                      objectFit:
                        "contain",
                      display:
                        "block",
                      mixBlendMode:
                        "screen",
                      opacity:
                        maskOpacity,
                      zIndex:
                        2,
                      pointerEvents:
                        "none",
                    }}
                  />
                )}
            </>
          )}

          {/* VIEW LABEL */}

          <div
            className="change-visual-label"
            style={{
              position:
                "absolute",
              zIndex:
                3,
            }}
          >
            {viewMode ===
              "before" &&
              "BEFORE IMAGERY"}

            {viewMode ===
              "after" &&
              "AFTER IMAGERY"}

            {viewMode ===
              "change" &&
              (showMask
                ? "AFTER + CHANGE MASK"
                : "AFTER — MASK HIDDEN")}
          </div>

        </div>

        {/* MASK CONTROLS */}

        <div className="mask-controls">

          <div className="mask-control-label">

            <span>
              CHANGE MASK
            </span>

            <strong>
              {viewMode ===
                "change"
                ? showMask
                  ? "ON"
                  : "OFF"
                : "VIEW CHANGE MODE"}
            </strong>

          </div>

          <input
            className="mask-opacity-slider"
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={
              maskOpacity
            }
            onChange={
              handleOpacityChange
            }
            disabled={
              viewMode !==
                "change" ||
              !showMask
            }
            aria-label="Change mask opacity"
          />

          <div className="mask-slider-scale">

            <span>
              0%
            </span>

            <span>
              {Math.round(
                maskOpacity *
                  100
              )}
              %
            </span>

            <span>
              100%
            </span>

          </div>

        </div>

        <div
          style={{
            marginTop:
              "10px",
            fontSize:
              "10px",
            letterSpacing:
              "0.07em",
            color:
              "#6b7280",
            fontWeight:
              700,
          }}
        >
          BEFORE → original
          observation&nbsp;&nbsp;|&nbsp;&nbsp;
          AFTER → later
          observation&nbsp;&nbsp;|&nbsp;&nbsp;
          CHANGE + MASK → detected
          temporal difference
        </div>

      </section>

      {/* ======================================================
          CHANGE SUMMARY
      ====================================================== */}

      <section className="scene-section">

        <div className="scene-section-heading">

          <div>

            <span className="section-label">
              CHANGE ANALYSIS
            </span>

            <h4>
              DETECTION SUMMARY
            </h4>

          </div>

        </div>

        <div
          className="evidence-grid"
        >

          <article className="evidence-card">

            <span className="evidence-label">
              DETECTED CHANGE
            </span>

            <strong>
              {formatPercentage(
                changePercentage
              )}
            </strong>

            <p>
              Changed pixels
            </p>

            <small>
              {changedPixels.toLocaleString()}
            </small>

          </article>

          <article className="evidence-card">

            <span className="evidence-label">
              CHANGE TYPE
            </span>

            <strong>
              {changeType}
            </strong>

            <p>
              Classification score
            </p>

            <small>
              {formatScore(
                classificationScore
              )}
            </small>

          </article>

          <article className="evidence-card">

            <span className="evidence-label">
              SEVERITY
            </span>

            <strong>
              {formatScore(
                severity
              )}
            </strong>

            <p>
              Evidence score
            </p>

            <small>
              {formatScore(
                evidenceScore
              )}
            </small>

          </article>

          <article className="evidence-card">

            <span className="evidence-label">
              DETECTED REGIONS
            </span>

            <strong>
              {changeRegions}
            </strong>

            <p>
              Analyst status
            </p>

            <small>
              {eventData?.analyst_status ??
                "UNREVIEWED"}
            </small>

          </article>

        </div>

      </section>

      {/* ======================================================
          EVENT EVIDENCE
      ====================================================== */}

      <section className="scene-section">

        <div className="scene-section-heading">

          <div>

            <span className="section-label">
              EVENT EVIDENCE
            </span>

            <h4>
              INTELLIGENCE METADATA
            </h4>

          </div>

        </div>

        <div className="evidence-grid">

          <article className="evidence-card">

            <span className="evidence-label">
              LOCATION
            </span>

            <strong>
              {locationLabel}
            </strong>

            <p>
              Dataset
            </p>

            <small>
              {datasetLabel}
            </small>

          </article>

          <article className="evidence-card">

            <span className="evidence-label">
              TEMPORAL WINDOW
            </span>

            <strong>
              {formatDate(
                beforeDate
              )}
            </strong>

            <p>
              After
            </p>

            <small>
              {formatDate(
                afterDate
              )}
            </small>

          </article>

          <article className="evidence-card">

            <span className="evidence-label">
              PRIORITY
            </span>

            <strong>
              {priority}
            </strong>

            <p>
              Severity score
            </p>

            <small>
              {formatScore(
                severity
              )}
            </small>

          </article>

          <article className="evidence-card">

            <span className="evidence-label">
              EVIDENCE CONFIDENCE
            </span>

            <strong>
              {confidence}
            </strong>

            <p>
              False-alarm risk
            </p>

            <small>
              {falseAlarmRisk}
            </small>

          </article>

        </div>

      </section>

      {/* ======================================================
          MODEL ANALYSIS
      ====================================================== */}

      <section className="analysis-summary">

        <div className="analysis-summary-header">

          <div>

            <span className="section-label">
              MODEL ANALYSIS
            </span>

            <h4>
              EVIDENCE SUMMARY
            </h4>

          </div>

          <span className="analysis-badge">
            MODEL GENERATED
          </span>

        </div>

        <div className="analysis-summary-content">

          <p>

            ORION detected{" "}

            <strong>
              {formatPercentage(
                changePercentage
              )}
            </strong>

            {" "}change between{" "}

            <strong>
              {formatDate(
                beforeDate
              )}
            </strong>

            {" "}and{" "}

            <strong>
              {formatDate(
                afterDate
              )}
            </strong>

            . The dominant
            classification is{" "}

            <strong>
              {changeType}
            </strong>

            {" "}with a classification
            score of{" "}

            <strong>
              {formatScore(
                classificationScore
              )}
            </strong>

            .

          </p>

          <div className="analysis-signals">

            <div>

              <span>
                EVIDENCE CONFIDENCE
              </span>

              <strong>
                {confidence}
              </strong>

            </div>

            <div>

              <span>
                FALSE-ALARM RISK
              </span>

              <strong>
                {falseAlarmRisk}
              </strong>

            </div>

            <div>

              <span>
                PRIORITY
              </span>

              <strong>
                {priority}
              </strong>

            </div>

          </div>

          {eventData?.false_alarm_reasons &&
            Array.isArray(
              eventData.false_alarm_reasons
            ) &&
            eventData
              .false_alarm_reasons
              .length > 0 && (

              <div
                style={{
                  marginTop:
                    "16px",
                  padding:
                    "12px 14px",
                  border:
                    "1px solid #e5e7eb",
                  borderRadius:
                    "8px",
                  background:
                    "#f9fafb",
                }}
              >

                <div
                  style={{
                    fontSize:
                      "9px",
                    fontWeight:
                      800,
                    letterSpacing:
                      "0.08em",
                    color:
                      "#6b7280",
                    marginBottom:
                      "7px",
                  }}
                >
                  FALSE-ALARM
                  CONSIDERATIONS
                </div>

                {eventData
                  .false_alarm_reasons
                  .map(
                    (
                      reason,
                      index
                    ) => (
                      <div
                        key={
                          index
                        }
                        style={{
                          fontSize:
                            "11px",
                          color:
                            "#4b5563",
                          marginBottom:
                            "4px",
                        }}
                      >
                        •{" "}
                        {String(
                          reason
                        )}
                      </div>
                    )
                  )}

              </div>
            )}

          <p className="analysis-disclaimer">
            These outputs are model-generated
            evidence and ranking signals. They
            should be reviewed by an analyst
            before being treated as a confirmed
            real-world change.
          </p>

        </div>

      </section>

      {/* ======================================================
          GEOSPATIAL CONTEXT
      ====================================================== */}

      <section className="scene-section">

        <div className="scene-section-heading">

          <div>

            <span className="section-label">
              GEOSPATIAL CONTEXT
            </span>

            <h4>
              SCENE LOCATION
            </h4>

          </div>

          <span className="coordinate-badge">
            {geospatialAvailable
              ? "WGS84"
              : "PIXEL GRID"}
          </span>

        </div>

        <div className="map-wrapper">

          <MapView
            scene={
              mapScene
            }
          />

        </div>

        <div className="geospatial-note">

          <strong>
            DATASET NOTE
          </strong>

          <span>

            {geospatialAvailable
              ? jewarMode
                ? "Sentinel-2 source imagery is georeferenced in EPSG:32643. ORION derives geographic context from the actual source raster and AOI."
                : "Source raster is georeferenced. ORION displays geographic coordinates derived from the source raster CRS."
              : "Current source imagery is not georeferenced. ORION therefore displays scene pixel coordinates rather than estimated latitude / longitude values."}

          </span>

        </div>

        {jewarMode && (
          <div
            style={{
              marginTop:
                "10px",
              padding:
                "11px 13px",
              border:
                "1px solid #e2e8f0",
              borderRadius:
                "8px",
              background:
                "#f8fafc",
              display:
                "flex",
              flexWrap:
                "wrap",
              gap:
                "12px",
              fontSize:
                "10px",
              color:
                "#475569",
              fontWeight:
                700,
            }}
          >

            <span>
              CRS:{" "}
              {getCRSLabel(
                eventData
              )}
            </span>

            <span>
              MGRS:{" "}
              {getMGRSLabel(
                eventData
              )}
            </span>

            <span>
              PIXEL SIZE:{" "}
              {getPixelSizeLabel(
                eventData
              )}
            </span>

            <span>
              SENSOR:{" "}
              {sensorLabel}
            </span>

          </div>
        )}

      </section>

      {/* ======================================================
          ANALYST REVIEW
      ====================================================== */}

      <section className="review-section">

        <div className="review-content">

          <span className="section-label">
            ANALYST REVIEW
          </span>

          <h4>
            REVIEW DETECTED CHANGE
          </h4>

          <p>
            Confirm or reject the detected
            event after reviewing the temporal
            imagery and change evidence.
          </p>

          <p
            style={{
              marginTop:
                "8px",
              fontSize:
                "11px",
              color:
                "#64748b",
            }}
          >
            Current status:{" "}
            <strong>
              {eventData?.analyst_status ??
                "UNREVIEWED"}
            </strong>
          </p>

        </div>

        <div className="review-actions">

          <button
            type="button"
            className="review-confirm"
            disabled
          >
            ✓ CONFIRM CHANGE
          </button>

          <button
            type="button"
            className="review-reject"
            disabled
          >
            ✕ REJECT CHANGE
          </button>

        </div>

      </section>

    </section>
  );
}

export default SceneDetail;