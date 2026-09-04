import { useState } from "react";
import MapView from "./MapView";

function SceneDetail({ scene, onBack }) {
  const [showChange, setShowChange] = useState(true);
  const [opacity, setOpacity] = useState(70);

  return (
    <section className="detail-section">

      {/* HEADER */}
      <div className="detail-header">

        <button
          className="back-button"
          onClick={onBack}
        >
          ← BACK TO RESULTS
        </button>

        <span className="section-label">
          03 / SCENE INTELLIGENCE
        </span>

      </div>


      {/* TITLE */}
      <div className="detail-title-row">

        <div>
          <h3>{scene.title}</h3>

          <p>
            {scene.id} · {scene.location}
          </p>
        </div>

        <div className="detail-match">
          <span>SEMANTIC MATCH</span>
          <strong>{scene.match}%</strong>
        </div>

      </div>


      {/* TEMPORAL IMAGERY */}
      <div className="temporal-grid">

        {/* BEFORE */}
        <div className="temporal-card">

          <div className="temporal-label">
            BEFORE
          </div>

          <div className="satellite-image before-image">

            <div className="image-grid"></div>

            <div className="terrain-shape shape-one"></div>
            <div className="terrain-shape shape-two"></div>
            <div className="terrain-shape shape-three"></div>

            <span className="image-label">
              SATELLITE
            </span>

          </div>

          <div className="temporal-date">
            {scene.beforeDate}
          </div>

        </div>


        {/* AFTER */}
        <div className="temporal-card">

          <div className="temporal-label">
            AFTER
          </div>

          <div className="satellite-image after-image">

            <div className="image-grid"></div>

            <div className="terrain-shape shape-one"></div>
            <div className="terrain-shape shape-two"></div>
            <div className="terrain-shape shape-three"></div>

            {/* Simulated detected structure */}
            {showChange && (
              <div
                className="change-overlay"
                style={{
                  opacity: opacity / 100
                }}
              >
                <span>CHANGE</span>
              </div>
            )}

            <span className="image-label">
              SATELLITE
            </span>

          </div>

          <div className="temporal-date">
            {scene.date}
          </div>

        </div>

      </div>


      {/* IMAGE CONTROLS */}
      <div className="image-controls">

        <div className="control-left">

          <button
            className={showChange ? "control-active" : ""}
            onClick={() => setShowChange(!showChange)}
          >
            {showChange ? "✓ CHANGE MASK ON" : "CHANGE MASK OFF"}
          </button>

        </div>


        <div className="opacity-control">

          <label>
            MASK OPACITY
            <strong>{opacity}%</strong>
          </label>

          <input
            type="range"
            min="0"
            max="100"
            value={opacity}
            onChange={(event) =>
              setOpacity(Number(event.target.value))
            }
          />

        </div>

      </div>


      {/* MAP */}
      <MapView scene={scene} />


      {/* INTELLIGENCE METADATA */}
      <div className="intelligence-grid">

        <div className="intelligence-card">
          <span>CHANGE TYPE</span>
          <strong>{scene.changeType}</strong>
        </div>

        <div className="intelligence-card">
          <span>AFFECTED AREA</span>
          <strong>{scene.affectedArea}</strong>
        </div>

        <div className="intelligence-card">
          <span>SENSOR</span>
          <strong>{scene.sensor}</strong>
        </div>

        <div className="intelligence-card">
          <span>RESOLUTION</span>
          <strong>{scene.resolution}</strong>
        </div>

      </div>


      {/* CONFIDENCE */}
      <div className="confidence-panel">

        <div className="confidence-heading">

          <div>
            <span>CHANGE CONFIDENCE</span>

            <strong>
              {scene.confidence}%
            </strong>
          </div>

          <span className="confidence-status">
            HIGH CONFIDENCE
          </span>

        </div>

        <div className="confidence-bar">
          <div
            style={{
              width: `${scene.confidence}%`
            }}
          />
        </div>

        <p>
          Confidence represents the system's estimated
          reliability after temporal comparison and
          quality screening.
        </p>

      </div>


      {/* SUMMARY */}
      <div className="description-panel">

        <span className="section-label">
          ANALYSIS SUMMARY
        </span>

        <p>
          {scene.description}
        </p>

      </div>


      {/* ANALYST REVIEW */}
      <div className="analyst-panel">

        <div>

          <span className="section-label">
            ANALYST REVIEW
          </span>

          <p>
            Review this detection and record an
            analyst decision for the audit trail.
          </p>

        </div>

        <div className="analyst-actions">

          <button className="confirm-button">
            ✓ CONFIRM CHANGE
          </button>

          <button className="reject-button">
            × REJECT
          </button>

        </div>

      </div>

    </section>
  );
}

export default SceneDetail;