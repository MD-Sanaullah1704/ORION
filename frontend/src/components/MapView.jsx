import {
  MapContainer,
  TileLayer,
  Rectangle,
  CircleMarker,
  Tooltip,
  Popup,
  ScaleControl,
  useMap,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import { useEffect } from "react";


/* ==========================================================
   FORMAT HELPERS
   ========================================================== */

function formatCoordinate(
  value,
  decimals = 6
) {
  if (
    value === undefined ||
    value === null ||
    Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return Number(value).toFixed(
    decimals
  );
}


function formatMeters(
  value,
  decimals = 2
) {
  if (
    value === undefined ||
    value === null ||
    Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return Number(value).toFixed(
    decimals
  );
}


/* ==========================================================
   UTM → WGS84
   ========================================================== */

/*
 * Converts UTM Easting/Northing to WGS84 latitude/longitude.
 *
 * This allows ORION to use the actual Sentinel-2 raster
 * footprint directly from EPSG:32643 without requiring
 * another frontend package.
 */

function utmToWgs84(
  easting,
  northing,
  zoneNumber,
  northernHemisphere = true
) {
  const a =
    6378137.0;

  const eccSquared =
    0.00669438;

  const k0 =
    0.9996;

  const e1 =
    (
      1 -
      Math.sqrt(
        1 - eccSquared
      )
    ) /
    (
      1 +
      Math.sqrt(
        1 - eccSquared
      )
    );

  let x =
    Number(easting) -
    500000.0;

  let y =
    Number(northing);

  if (
    !northernHemisphere
  ) {
    y -= 10000000.0;
  }

  const eccPrimeSquared =
    eccSquared /
    (
      1 -
      eccSquared
    );

  const M =
    y / k0;

  const mu =
    M /
    (
      a *
      (
        1 -
        eccSquared / 4 -
        3 *
          eccSquared *
          eccSquared /
          64 -
        5 *
          eccSquared *
          eccSquared *
          eccSquared /
          256
      )
    );

  const phi1Rad =
    mu +
    (
      3 *
        e1 /
        2 -
      27 *
        Math.pow(e1, 3) /
        32
    ) *
      Math.sin(
        2 * mu
      ) +
    (
      21 *
        e1 *
        e1 /
        16 -
      55 *
        Math.pow(e1, 4) /
        32
    ) *
      Math.sin(
        4 * mu
      ) +
    (
      151 *
        Math.pow(e1, 3) /
        96
    ) *
      Math.sin(
        6 * mu
      ) +
    (
      1097 *
        Math.pow(e1, 4) /
        512
    ) *
      Math.sin(
        8 * mu
      );

  const N1 =
    a /
    Math.sqrt(
      1 -
      eccSquared *
        Math.sin(
          phi1Rad
        ) *
        Math.sin(
          phi1Rad
        )
    );

  const T1 =
    Math.tan(
      phi1Rad
    ) *
    Math.tan(
      phi1Rad
    );

  const C1 =
    eccPrimeSquared *
    Math.cos(
      phi1Rad
    ) *
    Math.cos(
      phi1Rad
    );

  const R1 =
    a *
    (
      1 -
      eccSquared
    ) /
    Math.pow(
      1 -
        eccSquared *
          Math.sin(
            phi1Rad
          ) *
          Math.sin(
            phi1Rad
          ),
      1.5
    );

  const D =
    x /
    (
      N1 * k0
    );

  const lat =
    phi1Rad -
    (
      N1 *
      Math.tan(
        phi1Rad
      ) /
      R1
    ) *
      (
        D * D / 2 -
        (
          5 +
          3 * T1 +
          10 * C1 -
          4 * C1 * C1 -
          9 *
            eccPrimeSquared
        ) *
          Math.pow(
            D,
            4
          ) /
          24 +
        (
          61 +
          90 * T1 +
          298 * C1 +
          45 * T1 * T1 -
          252 *
            eccPrimeSquared -
          3 *
            C1 *
            C1
        ) *
          Math.pow(
            D,
            6
          ) /
          720
      );

  const lon =
    (
      D -
      (
        1 +
        2 * T1 +
        C1
      ) *
        Math.pow(
          D,
          3
        ) /
        6 +
      (
        5 -
        2 * C1 +
        28 * T1 -
        3 * C1 * C1 +
        8 *
          eccPrimeSquared +
        24 *
          T1 *
          T1
      ) *
        Math.pow(
          D,
          5
        ) /
        120
    ) /
    Math.cos(
      phi1Rad
    );

  const centralMeridian =
    (
      zoneNumber -
      1
    ) *
      6 -
    180 +
    3;

  return {
    latitude:
      (
        lat *
        180
      ) /
      Math.PI,

    longitude:
      centralMeridian +
      (
        lon *
        180
      ) /
      Math.PI,
  };
}


/* ==========================================================
   EXTRACT UTM ZONE FROM CRS
   ========================================================== */

function getUtmZone(
  crs
) {
  if (
    typeof crs !==
    "string"
  ) {
    return null;
  }

  const match =
    crs.match(
      /EPSG:326(\d{2})/i
    );

  if (!match) {
    return null;
  }

  return Number(
    match[1]
  );
}


/* ==========================================================
   CONVERT NATIVE RASTER BOUNDS TO WGS84
   ========================================================== */

function nativeBoundsToWgs84(
  nativeBounds,
  crs
) {
  if (
    !nativeBounds
  ) {
    return null;
  }

  const zone =
    getUtmZone(
      crs
    );

  /*
   * If the CRS is a northern UTM CRS, convert the four
   * raster corners.
   */

  if (
    zone &&
    nativeBounds.left !==
      undefined &&
    nativeBounds.right !==
      undefined &&
    nativeBounds.top !==
      undefined &&
    nativeBounds.bottom !==
      undefined
  ) {

    const corners = [

      utmToWgs84(
        nativeBounds.left,
        nativeBounds.top,
        zone,
        true
      ),

      utmToWgs84(
        nativeBounds.right,
        nativeBounds.top,
        zone,
        true
      ),

      utmToWgs84(
        nativeBounds.left,
        nativeBounds.bottom,
        zone,
        true
      ),

      utmToWgs84(
        nativeBounds.right,
        nativeBounds.bottom,
        zone,
        true
      ),

    ];


    const longitudes =
      corners.map(
        (point) =>
          point.longitude
      );

    const latitudes =
      corners.map(
        (point) =>
          point.latitude
      );


    return {
      west:
        Math.min(
          ...longitudes
        ),

      east:
        Math.max(
          ...longitudes
        ),

      south:
        Math.min(
          ...latitudes
        ),

      north:
        Math.max(
          ...latitudes
        ),
    };
  }


  /*
   * If the backend already provides WGS84-style bounds,
   * use them as a fallback.
   */

  if (
    nativeBounds.west !==
      undefined &&
    nativeBounds.east !==
      undefined &&
    nativeBounds.south !==
      undefined &&
    nativeBounds.north !==
      undefined
  ) {

    return {
      west:
        Number(
          nativeBounds.west
        ),

      east:
        Number(
          nativeBounds.east
        ),

      south:
        Number(
          nativeBounds.south
        ),

      north:
        Number(
          nativeBounds.north
        ),
    };
  }


  return null;
}


/* ==========================================================
   MAP VIEWPORT
   ========================================================== */

function MapViewport({
  bounds,
  center,
}) {
  const map =
    useMap();


  useEffect(() => {

    if (
      bounds &&
      Array.isArray(
        bounds
      ) &&
      bounds.length === 2
    ) {

      map.fitBounds(
        bounds,
        {
          padding: [
            30,
            30,
          ],
          maxZoom: 15,
        }
      );

      return;
    }


    if (
      center &&
      Array.isArray(
        center
      )
    ) {

      map.setView(
        center,
        14
      );
    }

  }, [
    map,
    bounds,
    center,
  ]);


  return null;
}


/* ==========================================================
   MAP VIEW
   ========================================================== */

function MapView({
  scene,
  datasetGeospatial = null,
}) {

  /* ========================================================
     MODE
     ======================================================== */

  const isDatasetMode =
    datasetGeospatial !==
    null;


  /* ========================================================
     EVENT GEOSPATIAL DATA
     ======================================================== */

  const eventGeospatial =
    scene?.geospatial ||
    null;


  /* ========================================================
     RASTER INFORMATION
     ======================================================== */

  const rasterInfo =
    isDatasetMode
      ? (
          datasetGeospatial
            ?.before
            ?.raster ||
          null
        )
      : (
          eventGeospatial
            ?.raster ||
          null
        );


  /* ========================================================
     STATUS
     ======================================================== */

  const isAvailable =
    isDatasetMode
      ? (
          datasetGeospatial
            ?.status ===
          "available"
        )
      : (
          eventGeospatial
            ?.status ===
          "available"
        );


  /* ========================================================
     CRS
     ======================================================== */

  const displayCrs =
    isDatasetMode
      ? (
          datasetGeospatial
            ?.before
            ?.raster
            ?.crs ||
          datasetGeospatial
            ?.after
            ?.raster
            ?.crs ||
          "Not available"
        )
      : (
          eventGeospatial
            ?.crs ||
          eventGeospatial
            ?.tile
            ?.source_crs ||
          eventGeospatial
            ?.raster
            ?.crs ||
          "Not available"
        );


  /* ========================================================
     RASTER DIMENSIONS
     ======================================================== */

  const rasterWidth =
    rasterInfo?.width ??
    null;

  const rasterHeight =
    rasterInfo?.height ??
    null;


  /* ========================================================
     PIXEL SIZE
     ======================================================== */

  const rasterPixelSize =
    rasterInfo?.pixel_size ||
    null;


  /* ========================================================
     NATIVE RASTER BOUNDS
     ======================================================== */

  const nativeRasterBounds =
    eventGeospatial
      ?.raster
      ?.bounds ||
    null;


  /* ========================================================
     FULL RASTER WGS84 FOOTPRINT
     
     IMPORTANT:
     
     This is the FULL SOURCE RASTER footprint.
     
     It is NOT the clipped change tile.
     ======================================================== */

  let rasterBounds =
    null;


  if (
    isDatasetMode
  ) {

    const aoi =
      datasetGeospatial
        ?.aoi_bbox_epsg4326;


    if (
      Array.isArray(
        aoi
      ) &&
      aoi.length >= 4
    ) {

      rasterBounds = {
        west:
          Number(
            aoi[0]
          ),

        south:
          Number(
            aoi[1]
          ),

        east:
          Number(
            aoi[2]
          ),

        north:
          Number(
            aoi[3]
          ),
      };
    }

  } else {

    rasterBounds =
      nativeBoundsToWgs84(
        nativeRasterBounds,
        displayCrs
      );


    /*
     * If conversion was not possible, try a backend-supplied
     * WGS84 raster footprint.
     */

    if (
      !rasterBounds
    ) {

      const backendBounds =
        eventGeospatial
          ?.raster
          ?.bounds_wgs84;


      if (
        backendBounds
      ) {

        rasterBounds = {
          west:
            Number(
              backendBounds.west
            ),

          south:
            Number(
              backendBounds.south
            ),

          east:
            Number(
              backendBounds.east
            ),

          north:
            Number(
              backendBounds.north
            ),
        };
      }
    }


    /*
     * Final fallback to the event bounds.
     *
     * This is only used if a full raster footprint is not
     * available.
     */

    if (
      !rasterBounds
    ) {

      const eventBounds =
        eventGeospatial
          ?.tile
          ?.bounds_wgs84;


      if (
        eventBounds
      ) {

        rasterBounds = {
          west:
            Number(
              eventBounds.west
            ),

          south:
            Number(
              eventBounds.south
            ),

          east:
            Number(
              eventBounds.east
            ),

          north:
            Number(
              eventBounds.north
            ),
        };
      }
    }
  }


  /* ========================================================
     EVENT / CHANGE AREA
     
     This is deliberately separate from the full raster.
     ======================================================== */

  const eventBounds =
    !isDatasetMode
      ? (
          eventGeospatial
            ?.tile
            ?.bounds_wgs84 ||
          null
        )
      : null;


  /* ========================================================
     GEOGRAPHIC CENTER
     ======================================================== */

  let latitude =
    null;

  let longitude =
    null;


  if (
    isDatasetMode
  ) {

    if (
      rasterBounds
    ) {

      longitude =
        (
          rasterBounds.west +
          rasterBounds.east
        ) / 2;

      latitude =
        (
          rasterBounds.south +
          rasterBounds.north
        ) / 2;
    }

  } else {

    /*
     * Prefer backend WGS84 center.
     */

    const center =
      eventGeospatial
        ?.tile
        ?.center_wgs84 ||
      eventGeospatial
        ?.center_wgs84 ||
      null;


    if (
      center
    ) {

      latitude =
        Number(
          center.latitude
        );

      longitude =
        Number(
          center.longitude
        );

    } else if (
      rasterBounds
    ) {

      latitude =
        (
          rasterBounds.south +
          rasterBounds.north
        ) / 2;

      longitude =
        (
          rasterBounds.west +
          rasterBounds.east
        ) / 2;
    }
  }


  /* ========================================================
     UTM CENTER
     ======================================================== */

  const nativeCenter =
    eventGeospatial
      ?.raster
      ?.center ||
    null;


  const easting =
    nativeCenter?.x ??
    null;


  const northing =
    nativeCenter?.y ??
    null;


  /* ========================================================
     LEAFLET FULL RASTER BOUNDS
     ======================================================== */

  const leafletRasterBounds =
    rasterBounds
      ? [
          [
            rasterBounds.south,
            rasterBounds.west,
          ],
          [
            rasterBounds.north,
            rasterBounds.east,
          ],
        ]
      : null;


  /* ========================================================
     LEAFLET EVENT BOUNDS
     ======================================================== */

  const leafletEventBounds =
    eventBounds
      ? [
          [
            Number(
              eventBounds.south
            ),
            Number(
              eventBounds.west
            ),
          ],
          [
            Number(
              eventBounds.north
            ),
            Number(
              eventBounds.east
            ),
          ],
        ]
      : null;


  /* ========================================================
     MAP CENTER
     ======================================================== */

  const center =
    latitude !== null &&
    longitude !== null
      ? [
          latitude,
          longitude,
        ]
      : [
          28.1755879,
          77.6050207,
        ];


  /* ========================================================
     DISPLAY TITLE
     ======================================================== */

  const displayTitle =
    isDatasetMode
      ? "DELHI SENTINEL-2 ANALYSIS AREA"
      : (
          scene?.location ||
          "NOIDA INTERNATIONAL AIRPORT AREA"
        );


  /* ========================================================
     DISPLAY STATUS
     ======================================================== */

  const displayStatus =
    isAvailable
      ? "GEOREFERENCED"
      : "GEOLOCATION UNAVAILABLE";


  /* ========================================================
     RETURN
     ======================================================== */

  return (
    <div
      className="map-panel"
      style={{
        width:
          "100%",
        background:
          "#ffffff",
        border:
          "1px solid #dbe3ec",
        borderRadius:
          "12px",
        overflow:
          "hidden",
      }}
    >

      {/* =====================================================
          HEADER
          ===================================================== */}

      <div
        className="map-header"
        style={{
          display:
            "flex",
          justifyContent:
            "space-between",
          alignItems:
            "center",
          gap:
            "20px",
          padding:
            "16px 20px",
          background:
            "#ffffff",
          borderBottom:
            "1px solid #e2e8f0",
        }}
      >

        <div>

          <span
            className="map-label"
            style={{
              display:
                "block",
              fontSize:
                "10px",
              fontWeight:
                800,
              letterSpacing:
                "0.14em",
              color:
                "#94a3b8",
              marginBottom:
                "6px",
            }}
          >
            GEOSPATIAL LOCATION
          </span>


          <strong
            style={{
              display:
                "block",
              fontSize:
                "15px",
              color:
                "#0f172a",
            }}
          >
            {displayTitle}
          </strong>

        </div>


        <span
          className={
            isAvailable
              ? "map-status"
              : "map-status map-status-unavailable"
          }
          style={{
            padding:
              "8px 12px",
            border:
              "1px solid #bbf7d0",
            background:
              "#f0fdf4",
            color:
              "#166534",
            fontSize:
              "10px",
            fontWeight:
              800,
            letterSpacing:
              "0.08em",
          }}
        >
          {displayStatus}
        </span>

      </div>


      {/* =====================================================
          MAP
          ===================================================== */}

      <div
        className="map-area"
        style={{
          width:
            "100%",
          height:
            "520px",
          position:
            "relative",
        }}
      >

        {isAvailable ? (

          <MapContainer
            center={
              center
            }
            zoom={
              14
            }
            scrollWheelZoom={
              true
            }
            style={{
              width:
                "100%",
              height:
                "100%",
            }}
          >

            {/* -------------------------------------------------
                BASE MAP
                ------------------------------------------------- */}

            <TileLayer
              attribution='&copy; OpenStreetMap contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />


            {/* -------------------------------------------------
                VIEWPORT
                ------------------------------------------------- */}

            <MapViewport
              bounds={
                leafletRasterBounds
              }
              center={
                center
              }
            />


            {/* =================================================
                FULL SOURCE RASTER
                ================================================= */}

            {leafletRasterBounds && (

              <Rectangle
                bounds={
                  leafletRasterBounds
                }
                pathOptions={{
                  color:
                    "#2563eb",
                  weight:
                    3,
                  opacity:
                    0.95,
                  fillColor:
                    "#3b82f6",
                  fillOpacity:
                    0.10,
                }}
              >

                <Tooltip
                  sticky
                >

                  <div
                    style={{
                      minWidth:
                        "210px",
                      lineHeight:
                        "1.5",
                    }}
                  >

                    <strong>
                      SOURCE RASTER FOOTPRINT
                    </strong>

                    <br />

                    CRS:{" "}
                    {displayCrs}

                    <br />

                    Raster:{" "}
                    {rasterWidth ??
                      "—"}
                    {" × "}
                    {rasterHeight ??
                      "—"}

                    <br />

                    Pixel:{" "}
                    {rasterPixelSize
                      ?.x !==
                    undefined
                      ? `${Math.abs(
                          Number(
                            rasterPixelSize.x
                          )
                        )} m`
                      : "—"}

                  </div>

                </Tooltip>

              </Rectangle>

            )}


            {/* =================================================
                DETECTED EVENT AREA
                ================================================= */}

            {leafletEventBounds && (

              <Rectangle
                bounds={
                  leafletEventBounds
                }
                pathOptions={{
                  color:
                    "#dc2626",
                  weight:
                    2,
                  opacity:
                    0.95,
                  dashArray:
                    "7 6",
                  fillColor:
                    "#ef4444",
                  fillOpacity:
                    0.08,
                }}
              >

                <Tooltip
                  sticky
                >

                  <div
                    style={{
                      minWidth:
                        "210px",
                      lineHeight:
                        "1.5",
                    }}
                  >

                    <strong>
                      DETECTED CHANGE AREA
                    </strong>

                    <br />

                    West:{" "}
                    {formatCoordinate(
                      eventBounds.west,
                      6
                    )}° E

                    <br />

                    East:{" "}
                    {formatCoordinate(
                      eventBounds.east,
                      6
                    )}° E

                    <br />

                    South:{" "}
                    {formatCoordinate(
                      eventBounds.south,
                      6
                    )}° N

                    <br />

                    North:{" "}
                    {formatCoordinate(
                      eventBounds.north,
                      6
                    )}° N

                  </div>

                </Tooltip>

              </Rectangle>

            )}


            {/* =================================================
                REAL LOCATION MARKER
                ================================================= */}

            {latitude !== null &&
              longitude !== null && (

              <CircleMarker
                center={[
                  latitude,
                  longitude,
                ]}
                radius={
                  8
                }
                pathOptions={{
                  color:
                    "#ffffff",
                  weight:
                    3,
                  fillColor:
                    "#111827",
                  fillOpacity:
                    1,
                }}
              >

                {/* ------------------------------------------------
                    HOVER TOOLTIP
                    ------------------------------------------------ */}

                <Tooltip
                  direction="right"
                  offset={[
                    12,
                    0,
                  ]}
                >

                  <div
                    style={{
                      minWidth:
                        "200px",
                      lineHeight:
                        "1.55",
                    }}
                  >

                    <strong>
                      ORION GEOLOCATION
                    </strong>

                    <br />

                    Latitude:{" "}
                    {formatCoordinate(
                      latitude,
                      7
                    )}° N

                    <br />

                    Longitude:{" "}
                    {formatCoordinate(
                      longitude,
                      7
                    )}° E

                  </div>

                </Tooltip>


                {/* ------------------------------------------------
                    CLICK POPUP
                    ------------------------------------------------ */}

                <Popup>

                  <div
                    style={{
                      minWidth:
                        "240px",
                      fontSize:
                        "12px",
                      lineHeight:
                        "1.7",
                    }}
                  >

                    <div
                      style={{
                        fontWeight:
                          800,
                        fontSize:
                          "14px",
                        marginBottom:
                          "8px",
                        color:
                          "#0f172a",
                      }}
                    >
                      ORION GEOLOCATION
                    </div>


                    <div>
                      <strong>
                        Latitude:
                      </strong>{" "}
                      {formatCoordinate(
                        latitude,
                        7
                      )}° N
                    </div>


                    <div>
                      <strong>
                        Longitude:
                      </strong>{" "}
                      {formatCoordinate(
                        longitude,
                        7
                      )}° E
                    </div>


                    <div>
                      <strong>
                        Easting:
                      </strong>{" "}
                      {formatMeters(
                        easting,
                        2
                      )} m
                    </div>


                    <div>
                      <strong>
                        Northing:
                      </strong>{" "}
                      {formatMeters(
                        northing,
                        2
                      )} m
                    </div>


                    <div>
                      <strong>
                        CRS:
                      </strong>{" "}
                      {displayCrs}
                    </div>


                    <div>
                      <strong>
                        Pixel size:
                      </strong>{" "}
                      {rasterPixelSize
                        ?.x !==
                      undefined
                        ? `${Math.abs(
                            Number(
                              rasterPixelSize.x
                            )
                          )} m`
                        : "—"}
                    </div>


                    <div>
                      <strong>
                        Raster:
                      </strong>{" "}
                      {rasterWidth ??
                        "—"}
                      {" × "}
                      {rasterHeight ??
                        "—"}
                    </div>

                  </div>

                </Popup>

              </CircleMarker>

            )}


            {/* -------------------------------------------------
                SCALE
                ------------------------------------------------- */}

            <ScaleControl
              position="bottomleft"
              imperial={
                false
              }
            />

          </MapContainer>

        ) : (

          /* ===================================================
             UNAVAILABLE STATE
             =================================================== */

          <div
            style={{
              width:
                "100%",
              height:
                "100%",
              display:
                "flex",
              alignItems:
                "center",
              justifyContent:
                "center",
              background:
                "#f8fafc",
              color:
                "#64748b",
              textAlign:
                "center",
            }}
          >

            <div>

              <div
                style={{
                  fontSize:
                    "12px",
                  fontWeight:
                    800,
                  letterSpacing:
                    "0.08em",
                  marginBottom:
                    "8px",
                }}
              >
                GEOLOCATION UNAVAILABLE
              </div>


              <div
                style={{
                  fontSize:
                    "12px",
                }}
              >
                Source raster has no valid
                georeferencing.
              </div>

            </div>

          </div>

        )}

      </div>


      {/* =====================================================
          PRIMARY GEOSPATIAL INFORMATION
          ===================================================== */}

      <div
        className="map-geospatial-info"
        style={{
          display:
            "grid",
          gridTemplateColumns:
            "repeat(4, minmax(0, 1fr))",
          borderTop:
            "1px solid #e2e8f0",
        }}
      >

        {/* STATUS */}

        <div
          className="geospatial-item"
          style={{
            padding:
              "17px 18px",
            borderRight:
              "1px solid #e2e8f0",
          }}
        >

          <span>
            STATUS
          </span>

          <strong
            style={{
              color:
                isAvailable
                  ? "#166534"
                  : "#991b1b",
            }}
          >
            {isAvailable
              ? "AVAILABLE"
              : "UNAVAILABLE"}
          </strong>

        </div>


        {/* CRS */}

        <div
          className="geospatial-item"
          style={{
            padding:
              "17px 18px",
            borderRight:
              "1px solid #e2e8f0",
          }}
        >

          <span>
            CRS
          </span>

          <strong>
            {displayCrs}
          </strong>

        </div>


        {/* LATITUDE */}

        <div
          className="geospatial-item"
          style={{
            padding:
              "17px 18px",
            borderRight:
              "1px solid #e2e8f0",
          }}
        >

          <span>
            LATITUDE
          </span>

          <strong>
            {isAvailable
              ? `${formatCoordinate(
                  latitude,
                  7
                )}° N`
              : "—"}
          </strong>

        </div>


        {/* LONGITUDE */}

        <div
          className="geospatial-item"
          style={{
            padding:
              "17px 18px",
          }}
        >

          <span>
            LONGITUDE
          </span>

          <strong>
            {isAvailable
              ? `${formatCoordinate(
                  longitude,
                  7
                )}° E`
              : "—"}
          </strong>

        </div>

      </div>


      {/* =====================================================
          UTM / RASTER INFORMATION
          ===================================================== */}

      {!isDatasetMode &&
        isAvailable && (

        <div
          className="map-geospatial-info"
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(4, minmax(0, 1fr))",
            borderTop:
              "1px solid #e2e8f0",
            background:
              "#f8fafc",
          }}
        >

          {/* EASTING */}

          <div
            className="geospatial-item"
            style={{
              padding:
                "15px 18px",
              borderRight:
                "1px solid #e2e8f0",
            }}
          >

            <span>
              EASTING
            </span>

            <strong>
              {formatMeters(
                easting,
                2
              )} m
            </strong>

          </div>


          {/* NORTHING */}

          <div
            className="geospatial-item"
            style={{
              padding:
                "15px 18px",
              borderRight:
                "1px solid #e2e8f0",
            }}
          >

            <span>
              NORTHING
            </span>

            <strong>
              {formatMeters(
                northing,
                2
              )} m
            </strong>

          </div>


          {/* PIXEL SIZE */}

          <div
            className="geospatial-item"
            style={{
              padding:
                "15px 18px",
              borderRight:
                "1px solid #e2e8f0",
            }}
          >

            <span>
              PIXEL SIZE
            </span>

            <strong>
              {rasterPixelSize
                ?.x !==
              undefined
                ? `${Math.abs(
                    Number(
                      rasterPixelSize.x
                    )
                  )} × ${Math.abs(
                    Number(
                      rasterPixelSize.y ??
                      rasterPixelSize.x
                    )
                  )} m`
                : "—"}
            </strong>

          </div>


          {/* RASTER SIZE */}

          <div
            className="geospatial-item"
            style={{
              padding:
                "15px 18px",
            }}
          >

            <span>
              RASTER SIZE
            </span>

            <strong>
              {rasterWidth ??
                "—"}
              {" × "}
              {rasterHeight ??
                "—"}
              {" pixels"}
            </strong>

          </div>

        </div>

      )}


      {/* =====================================================
          DATASET METADATA
          ===================================================== */}

      {isDatasetMode && (

        <div
          className="map-geospatial-info"
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(4, minmax(0, 1fr))",
            borderTop:
              "1px solid #e2e8f0",
          }}
        >

          <div
            className="geospatial-item"
            style={{
              padding:
                "15px 18px",
              borderRight:
                "1px solid #e2e8f0",
            }}
          >

            <span>
              SENSOR
            </span>

            <strong>
              Sentinel-2
            </strong>

          </div>


          <div
            className="geospatial-item"
            style={{
              padding:
                "15px 18px",
              borderRight:
                "1px solid #e2e8f0",
            }}
          >

            <span>
              MGRS
            </span>

            <strong>
              {datasetGeospatial
                ?.before
                ?.mgrs_tile ||
                "—"}
            </strong>

          </div>


          <div
            className="geospatial-item"
            style={{
              padding:
                "15px 18px",
              borderRight:
                "1px solid #e2e8f0",
            }}
          >

            <span>
              PIXEL SIZE
            </span>

            <strong>
              {rasterPixelSize
                ?.x !==
              undefined
                ? `${Math.abs(
                    Number(
                      rasterPixelSize.x
                    )
                  )} m`
                : "—"}
            </strong>

          </div>


          <div
            className="geospatial-item"
            style={{
              padding:
                "15px 18px",
            }}
          >

            <span>
              RASTER
            </span>

            <strong>
              {rasterWidth &&
              rasterHeight
                ? `${rasterWidth} × ${rasterHeight}`
                : "—"}
            </strong>

          </div>

        </div>

      )}


      {/* =====================================================
          WGS84 SOURCE RASTER BOUNDS
          ===================================================== */}

      {isAvailable &&
        rasterBounds && (

        <div
          className="map-bounds"
          style={{
            padding:
              "18px",
            borderTop:
              "1px solid #e2e8f0",
            background:
              "#ffffff",
          }}
        >

          <div
            className="bounds-title"
            style={{
              fontSize:
                "10px",
              fontWeight:
                800,
              letterSpacing:
                "0.12em",
              color:
                "#64748b",
              marginBottom:
                "12px",
            }}
          >
            SOURCE RASTER BOUNDS · WGS84
          </div>


          <div
            className="bounds-grid"
            style={{
              display:
                "grid",
              gridTemplateColumns:
                "repeat(4, minmax(0, 1fr))",
              gap:
                "10px",
            }}
          >

            <div>

              <span>
                WEST
              </span>

              <strong>
                {formatCoordinate(
                  rasterBounds.west,
                  7
                )}° E
              </strong>

            </div>


            <div>

              <span>
                EAST
              </span>

              <strong>
                {formatCoordinate(
                  rasterBounds.east,
                  7
                )}° E
              </strong>

            </div>


            <div>

              <span>
                SOUTH
              </span>

              <strong>
                {formatCoordinate(
                  rasterBounds.south,
                  7
                )}° N
              </strong>

            </div>


            <div>

              <span>
                NORTH
              </span>

              <strong>
                {formatCoordinate(
                  rasterBounds.north,
                  7
                )}° N
              </strong>

            </div>

          </div>

        </div>

      )}


      {/* =====================================================
          TEMPORAL DATASET INFORMATION
          ===================================================== */}

      {isDatasetMode && (

        <div
          className="map-bounds"
          style={{
            borderTop:
              "1px solid #e2e8f0",
            padding:
              "18px",
          }}
        >

          <div
            className="bounds-title"
            style={{
              fontSize:
                "10px",
              fontWeight:
                800,
              letterSpacing:
                "0.12em",
              color:
                "#64748b",
              marginBottom:
                "12px",
            }}
          >
            TEMPORAL COVERAGE
          </div>


          <div
            className="bounds-grid"
            style={{
              display:
                "grid",
              gridTemplateColumns:
                "repeat(4, minmax(0, 1fr))",
              gap:
                "10px",
            }}
          >

            <div>

              <span>
                BEFORE
              </span>

              <strong>
                {datasetGeospatial
                  ?.before
                  ?.date
                  ? datasetGeospatial
                      .before
                      .date
                      .split(
                        "T"
                      )[0]
                  : "—"}
              </strong>

            </div>


            <div>

              <span>
                AFTER
              </span>

              <strong>
                {datasetGeospatial
                  ?.after
                  ?.date
                  ? datasetGeospatial
                      .after
                      .date
                      .split(
                        "T"
                      )[0]
                  : "—"}
              </strong>

            </div>


            <div>

              <span>
                BEFORE CLOUD
              </span>

              <strong>
                {datasetGeospatial
                  ?.before
                  ?.cloud_cover !==
                undefined
                  ? `${(
                      Number(
                        datasetGeospatial
                          .before
                          .cloud_cover
                      ) *
                      100
                    ).toFixed(
                      3
                    )}%`
                  : "—"}
              </strong>

            </div>


            <div>

              <span>
                AFTER CLOUD
              </span>

              <strong>
                {datasetGeospatial
                  ?.after
                  ?.cloud_cover !==
                undefined
                  ? `${(
                      Number(
                        datasetGeospatial
                          .after
                          .cloud_cover
                      ) *
                      100
                    ).toFixed(
                      3
                    )}%`
                  : "—"}
              </strong>

            </div>

          </div>

        </div>

      )}


      {/* =====================================================
          LEGEND
          ===================================================== */}

      <div
        className="map-legend"
        style={{
          display:
            "flex",
          gap:
            "24px",
          flexWrap:
            "wrap",
          padding:
            "14px 18px",
          borderTop:
            "1px solid #e2e8f0",
          background:
            "#f8fafc",
          fontSize:
            "10px",
          fontWeight:
            700,
          letterSpacing:
            "0.04em",
          color:
            "#475569",
        }}
      >

        <div
          style={{
            display:
              "flex",
            alignItems:
              "center",
            gap:
              "7px",
          }}
        >

          <span
            style={{
              width:
                "14px",
              height:
                "10px",
              border:
                "2px solid #2563eb",
              background:
                "rgba(59,130,246,0.10)",
              display:
                "inline-block",
            }}
          ></span>

          SOURCE RASTER

        </div>


        {!isDatasetMode && (
          <div
            style={{
              display:
                "flex",
              alignItems:
                "center",
              gap:
                "7px",
            }}
          >

            <span
              style={{
                width:
                  "14px",
                height:
                  "10px",
                border:
                  "2px dashed #dc2626",
                background:
                  "rgba(239,68,68,0.08)",
                display:
                  "inline-block",
              }}
            ></span>

            DETECTED CHANGE AREA

          </div>
        )}


        <div
          style={{
            display:
              "flex",
            alignItems:
              "center",
            gap:
              "7px",
          }}
        >

          <span
            style={{
              width:
                "10px",
              height:
                "10px",
              borderRadius:
                "50%",
              background:
                "#111827",
              border:
                "2px solid #ffffff",
              boxShadow:
                "0 0 0 1px #111827",
              display:
                "inline-block",
            }}
          ></span>

          SCENE LOCATION

        </div>

      </div>

    </div>
  );
}


export default MapView;