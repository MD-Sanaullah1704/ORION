function MapView({ scene }) {
  return (
    <div className="map-panel">

      <div className="map-header">
        <div>
          <span className="map-label">
            GEOSPATIAL LOCATION
          </span>

          <strong>
            {scene.location}
          </strong>
        </div>

        <span className="map-status">
          CHANGE DETECTED
        </span>
      </div>


      <div className="map-area">

        {/* Grid */}
        <div className="map-grid"></div>

        {/* Simulated terrain */}
        <div className="terrain terrain-one"></div>
        <div className="terrain terrain-two"></div>
        <div className="terrain terrain-three"></div>

        {/* Change detection area */}
        <div className="change-zone">
          <span>CHANGE</span>
        </div>

        {/* Scene marker */}
        <div className="scene-marker">
          <div className="marker-pulse"></div>
          <div className="marker-dot"></div>
        </div>

        {/* Coordinate label */}
        <div className="coordinate-label">
          {scene.location}
        </div>

        {/* Map scale */}
        <div className="map-scale">
          <span></span>
          1 km
        </div>

      </div>


      <div className="map-legend">

        <div>
          <span className="legend-marker detected"></span>
          DETECTED CHANGE
        </div>

        <div>
          <span className="legend-marker location"></span>
          SCENE LOCATION
        </div>

        <div>
          <span className="legend-marker boundary"></span>
          ANALYSIS AREA
        </div>

      </div>

    </div>
  );
}

export default MapView;