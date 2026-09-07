import {
  useEffect,
  useState,
} from "react";

import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
  Navigate,
  useLocation,
  useNavigate,
} from "react-router-dom";

import SearchPage from "./pages/SearchPage";
import ResultsPage from "./pages/ResultsPage";
import ChangesPage from "./pages/ChangesPage";
import ReviewPage from "./pages/ReviewPage";
import SceneDetail from "./components/SceneDetail";
import MapView from "./components/MapView";
import IngestionPage from "./pages/IngestionPage";


const API_BASE_URL =
  "http://127.0.0.1:8000";


/* ==========================================================
   SEARCH RESPONSE NORMALIZATION
   ========================================================== */

function normalizeSearchResponse(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (
    Array.isArray(
      data?.results?.results
    )
  ) {
    return data.results.results;
  }

  if (
    Array.isArray(
      data?.results
    )
  ) {
    return data.results;
  }

  if (
    Array.isArray(
      data?.matches
    )
  ) {
    return data.matches;
  }

  if (
    Array.isArray(
      data?.data
    )
  ) {
    return data.data;
  }

  return [];
}


/* ==========================================================
   TILE COORDINATES
   ========================================================== */

function extractTileCoordinates(
  tileId
) {
  if (
    typeof tileId !==
    "string"
  ) {
    return {
      x: "—",
      y: "—",
    };
  }

  const match =
    tileId.match(
      /_x(\d+)_y(\d+)/
    );

  if (!match) {
    return {
      x: "—",
      y: "—",
    };
  }

  return {
    x: match[1],
    y: match[2],
  };
}


/* ==========================================================
   NUMERIC EVENT TILE ID
   ========================================================== */

function extractNumericTileId(
  tileId
) {
  if (
    typeof tileId ===
    "number"
  ) {
    return tileId;
  }

  if (
    typeof tileId !==
    "string"
  ) {
    return null;
  }

  const match =
    tileId.match(
      /tile_(\d+)_x/i
    );

  if (!match) {
    return null;
  }

  return Number(
    match[1]
  );
}


/* ==========================================================
   SEARCH RESULT → SCENE
   ========================================================== */

function resultToScene(
  result,
  index
) {
  const tileId =
    result?.tile_id ??
    result?.tile_index ??
    result?.id ??
    `unknown-${index}`;

  const score =
    typeof result?.score ===
    "number"
      ? result.score
      : typeof result?.similarity ===
        "number"
      ? result.similarity
      : 0;

  const semanticScore =
    typeof result?.semantic_score ===
    "number"
      ? result.semantic_score
      : score;

  const metadataScore =
    typeof result?.metadata_score ===
    "number"
      ? result.metadata_score
      : 0;

  const finalScore =
    typeof result?.final_score ===
    "number"
      ? result.final_score
      : score;

  const coordinates =
    extractTileCoordinates(
      tileId
    );

  const eventTileId =
    extractNumericTileId(
      tileId
    );

  const dataset =
    result?.dataset ??
    (
      String(tileId)
        .toLowerCase()
        .startsWith(
          "jewar"
        )
        ? "jewar_airport_best"
        : "prayagraj"
    );

  const isJewar =
    dataset ===
    "jewar_airport_best";

  const location =
    result?.location ??
    (
      isJewar
        ? "Noida International Airport Area, Jewar, Uttar Pradesh"
        : `PIXEL COORDINATES X:${coordinates.x} Y:${coordinates.y}`
    );

  const date =
    result?.date ??
    result?.after_date ??
    (
      isJewar
        ? "2023-10-06"
        : "2025-01-27"
    );

  const beforeDate =
    result?.before_date ??
    (
      isJewar
        ? "2022-12-10"
        : "2024-12-13"
    );

  const sensor =
    result?.sensor ??
    (
      isJewar
        ? "COPERNICUS SENTINEL-2"
        : "RGB SATELLITE IMAGERY"
    );

  const resolution =
    result?.pixel_size_m
      ? `${result.pixel_size_m} m`
      : result?.tile_size
      ? `${result.tile_size} × ${result.tile_size} TILE`
      : isJewar
      ? "10 m"
      : "256 × 256 TILE";

  const changeType =
    result?.change_type ??
    result?.changeType ??
    (
      result?.query_tags?.length
        ? result.query_tags[0]
        : "SEMANTIC MATCH"
    );

  const confidence =
    typeof result?.confidence ===
    "number"
      ? result.confidence
      : Math.round(
          finalScore * 100
        );

  const queryTags =
    Array.isArray(
      result?.query_tags
    )
      ? result.query_tags
      : [];

  const tags =
    queryTags.length > 0
      ? [
          ...queryTags.slice(
            0,
            4
          ),
          `SCORE ${finalScore.toFixed(
            3
          )}`,
        ]
      : [
          "SEMANTIC MATCH",
          `SCORE ${finalScore.toFixed(
            3
          )}`,
        ];

  return {
    id:
      `ORION-TILE-${String(
        index + 1
      ).padStart(3, "0")}`,

    tileId,

    eventTileId,

    title:
      isJewar
        ? "Noida International Airport Area"
        : `Satellite Tile ${String(
            tileId
          )}`,

    rank:
      result?.rank ??
      index + 1,

    match:
      Math.round(
        finalScore * 100
      ),

    score: finalScore,

    semanticScore,

    metadataScore,

    finalScore,

    location,

    x:
      result?.x ??
      coordinates.x,

    y:
      result?.y ??
      coordinates.y,

    date,

    beforeDate,

    sensor,

    platform:
      result?.platform ??
      (
        isJewar
          ? "Sentinel-2"
          : "—"
      ),

    product:
      result?.product ??
      (
        isJewar
          ? "Sentinel-2 Level-2A Surface Reflectance"
          : "RGB satellite imagery"
      ),

    resolution,

    changeType,

    confidence,

    affectedArea:
      result?.affected_area ??
      "—",

    description:
      isJewar
        ? `Semantic retrieval matched the Jewar airport construction area to the query with a final score of ${finalScore.toFixed(
            4
          )}.`
        : `Semantic retrieval matched this satellite tile to the query with a final score of ${finalScore.toFixed(
            4
          )}.`,

    tags,

    queryTags,

    dataset,

    sceneId:
      result?.scene_id ??
      (
        isJewar
          ? "jewar_airport_best"
          : "prayagraj"
      ),

    observation:
      result?.observation ??
      (
        isJewar
          ? "full_aoi_preview"
          : "before"
      ),

    sourceRaster:
      result?.source_raster ??
      (
        isJewar
          ? "B04.tif"
          : "before.tif"
      ),

    tileSize:
      result?.tile_size ??
      256,

    filename:
      result?.filename ??
      "",

    path:
      result?.path ??
      "",

    mgrsTile:
      result?.mgrs_tile ??
      "",

    sourceCrs:
      result?.source_crs ??
      "",

    pixelSizeM:
      result?.pixel_size_m ??
      null,

    imageRole:
      result?.image_role ??
      "",

    rawResult:
      result,
  };
}


/* ==========================================================
   DATASET DETAIL PAGE
   ========================================================== */

function DatasetDetailPage() {
  const [
    datasetGeospatial,
    setDatasetGeospatial,
  ] = useState(null);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState("");

  const datasetId =
    "delhi_sentinel2";


  useEffect(() => {
    let cancelled = false;

    async function loadDatasetGeospatial() {
      try {
        setLoading(true);
        setError("");

        const response =
          await fetch(
            `${API_BASE_URL}/datasets/${datasetId}/geospatial`
          );

        if (!response.ok) {
          const errorText =
            await response.text();

          throw new Error(
            `HTTP ${response.status}: ${errorText}`
          );
        }

        const data =
          await response.json();

        if (!cancelled) {
          setDatasetGeospatial(
            data
          );
        }

      } catch (requestError) {
        console.error(
          "ORION dataset geospatial request failed:",
          requestError
        );

        if (!cancelled) {
          setDatasetGeospatial(
            null
          );

          setError(
            "Unable to load Delhi dataset geospatial information. Check that the ORION backend is running."
          );
        }

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadDatasetGeospatial();

    return () => {
      cancelled = true;
    };
  }, []);


  return (
    <section className="orion-page">

      {/* ====================================================
          PAGE HEADER
          ==================================================== */}

      <div className="page-header">

        <div>

          <span className="eyebrow">
            DATASET
          </span>

          <h2>
            Delhi Sentinel-2 Dataset
          </h2>

          <p>
            Geospatial footprint and temporal
            provenance for the locally staged
            Sentinel-2 analysis pair.
          </p>

        </div>

      </div>


      {/* ====================================================
          LOADING
          ==================================================== */}

      {loading && (

        <div className="page-message">

          <p>
            LOADING DATASET GEOSPATIAL
            INFORMATION...
          </p>

        </div>

      )}


      {/* ====================================================
          ERROR
          ==================================================== */}

      {!loading &&
        error && (

          <div className="page-message">

            <p>
              {error}
            </p>

          </div>

        )}


      {/* ====================================================
          DATASET CONTENT
          ==================================================== */}

      {!loading &&
        !error &&
        datasetGeospatial && (

          <>

            {/* ------------------------------------------------
                STATUS
                ------------------------------------------------ */}

            <div className="results-section">

              <div className="section-header">

                <div>

                  <span className="eyebrow">
                    DATASET STATUS
                  </span>

                  <h3>
                    {datasetGeospatial.status ===
                    "available"
                      ? "GEOREFERENCED DATASET"
                      : "GEOLOCATION UNAVAILABLE"}
                  </h3>

                </div>

              </div>


              <div className="result-grid">

                <div className="result-card">

                  <span>
                    DATASET ID
                  </span>

                  <strong>
                    {datasetGeospatial.dataset_id}
                  </strong>

                </div>


                <div className="result-card">

                  <span>
                    SENSOR
                  </span>

                  <strong>
                    {datasetGeospatial.sensor}
                  </strong>

                </div>


                <div className="result-card">

                  <span>
                    PRODUCT
                  </span>

                  <strong>
                    {datasetGeospatial.product}
                  </strong>

                </div>


                <div className="result-card">

                  <span>
                    MGRS TILE
                  </span>

                  <strong>
                    {datasetGeospatial
                      ?.before
                      ?.mgrs_tile ??
                      "—"}
                  </strong>

                </div>

              </div>

            </div>


            {/* ------------------------------------------------
                REAL GEOSPATIAL MAP
                ------------------------------------------------ */}

            <MapView
              datasetGeospatial={
                datasetGeospatial
              }

              scene={{
                location:
                  "DELHI SENTINEL-2"
              }}
            />


            {/* ------------------------------------------------
                ACQUISITION INFORMATION
                ------------------------------------------------ */}

            <div className="results-section">

              <div className="section-header">

                <div>

                  <span className="eyebrow">
                    TEMPORAL PAIR
                  </span>

                  <h3>
                    BEFORE / AFTER ACQUISITIONS
                  </h3>

                </div>

              </div>


              <div className="result-grid">

                {/* BEFORE */}

                <div className="result-card">

                  <span>
                    BEFORE DATE
                  </span>

                  <strong>
                    {datasetGeospatial
                      ?.before
                      ?.date
                      ?.split("T")[0] ??
                      "—"}
                  </strong>

                  <small>
                    {datasetGeospatial
                      ?.before
                      ?.scene_id ??
                      "—"}
                  </small>

                </div>


                {/* AFTER */}

                <div className="result-card">

                  <span>
                    AFTER DATE
                  </span>

                  <strong>
                    {datasetGeospatial
                      ?.after
                      ?.date
                      ?.split("T")[0] ??
                      "—"}
                  </strong>

                  <small>
                    {datasetGeospatial
                      ?.after
                      ?.scene_id ??
                      "—"}
                  </small>

                </div>


                {/* BEFORE CLOUD */}

                <div className="result-card">

                  <span>
                    BEFORE CLOUD COVER
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
                          ) * 100
                        ).toFixed(3)}%`
                      : "—"}
                  </strong>

                </div>


                {/* AFTER CLOUD */}

                <div className="result-card">

                  <span>
                    AFTER CLOUD COVER
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
                          ) * 100
                        ).toFixed(3)}%`
                      : "—"}
                  </strong>

                </div>

              </div>

            </div>


            {/* ------------------------------------------------
                RASTER INFORMATION
                ------------------------------------------------ */}

            <div className="results-section">

              <div className="section-header">

                <div>

                  <span className="eyebrow">
                    RASTER PROVENANCE
                  </span>

                  <h3>
                    LOCAL GEOTIFF INFORMATION
                  </h3>

                </div>

              </div>


              <div className="result-grid">

                <div className="result-card">

                  <span>
                    CRS
                  </span>

                  <strong>
                    {datasetGeospatial
                      ?.before
                      ?.raster
                      ?.crs ??
                      "—"}
                  </strong>

                </div>


                <div className="result-card">

                  <span>
                    PIXEL SIZE
                  </span>

                  <strong>
                    {datasetGeospatial
                      ?.before
                      ?.raster
                      ?.pixel_size
                      ?.x !==
                    undefined
                      ? `${Math.abs(
                          Number(
                            datasetGeospatial
                              .before
                              .raster
                              .pixel_size
                              .x
                          )
                        )} m`
                      : "—"}
                  </strong>

                </div>


                <div className="result-card">

                  <span>
                    RASTER SIZE
                  </span>

                  <strong>
                    {datasetGeospatial
                      ?.before
                      ?.raster
                      ?.width &&
                    datasetGeospatial
                      ?.before
                      ?.raster
                      ?.height
                      ? `${datasetGeospatial.before.raster.width} × ${datasetGeospatial.before.raster.height}`
                      : "—"}
                  </strong>

                </div>


                <div className="result-card">

                  <span>
                    BANDS
                  </span>

                  <strong>
                    {datasetGeospatial
                      ?.before
                      ?.raster
                      ?.count ??
                      "—"}
                  </strong>

                </div>

              </div>

            </div>


            {/* ------------------------------------------------
                OFFLINE PROVENANCE
                ------------------------------------------------ */}

            <div className="results-section">

              <div className="section-header">

                <div>

                  <span className="eyebrow">
                    OFFLINE OPERATION
                  </span>

                  <h3>
                    LOCAL DATA READY
                  </h3>

                </div>

              </div>


              <div className="page-message">

                <p>
                  {datasetGeospatial
                    .offline_note ??
                    "Network access is used only during dataset staging. ORION runtime uses locally saved imagery and provenance."}
                </p>

              </div>

            </div>

          </>

        )}

    </section>
  );
}


/* ==========================================================
   APP LAYOUT
   ========================================================== */

function AppLayout({
  query,
  setQuery,
  results,
  loading,
  error,
  onSearch,
}) {
  const location =
    useLocation();

  const navigate =
    useNavigate();

  const isScene =
    location.pathname.startsWith(
      "/scene/"
    );

  const isDataset =
    location.pathname.startsWith(
      "/dataset/"
    );


  return (
    <div className="app">

      {/* ====================================================
          HEADER
          ==================================================== */}

      <header className="top-header">

        <div>

          <h1>
            ORION
          </h1>

          <p>
            OFFLINE SATELLITE INTELLIGENCE
          </p>

        </div>


        <div className="system-status">

          <span className="status-dot"></span>

          {loading
            ? "SEARCHING..."
            : "SYSTEM READY"}

        </div>

      </header>


      {/* ====================================================
          NAVIGATION
          ==================================================== */}

      <nav className="orion-navigation">

        <NavLink
          to="/search"
          className={({ isActive }) =>
            isActive
              ? "nav-item active"
              : "nav-item"
          }
        >
          SEARCH
        </NavLink>


        <NavLink
          to="/results"
          className={({ isActive }) =>
            isActive
              ? "nav-item active"
              : "nav-item"
          }
        >
          RESULTS
        </NavLink>


        <button
          className={
            isScene
              ? "nav-item active"
              : "nav-item"
          }

          disabled={!isScene}

          onClick={() =>
            navigate(-1)
          }
        >
          SCENE
        </button>


        <NavLink
          to="/changes"
          className={({ isActive }) =>
            isActive
              ? "nav-item active"
              : "nav-item"
          }
        >
          CHANGES
        </NavLink>


        <NavLink
          to="/review"
          className={({ isActive }) =>
            isActive
              ? "nav-item active"
              : "nav-item"
          }
        >
          REVIEW
        </NavLink>


        {/* ==================================================
            DATASET
            ================================================== */}

        <NavLink
          to="/dataset/delhi_sentinel2"
          className={({ isActive }) =>
            isActive
              ? "nav-item active"
              : "nav-item"
          }
        >
          DATASET
        </NavLink>


        {/* ==================================================
            INCREMENTAL INGESTION
            ================================================== */}

        <NavLink
          to="/ingest"
          className={({ isActive }) =>
            isActive
              ? "nav-item active"
              : "nav-item"
          }
        >
          INGEST
        </NavLink>

      </nav>


      {/* ====================================================
          MAIN ROUTES
          ==================================================== */}

      <main>

        <Routes>

          {/* =================================================
              SEARCH
              ================================================= */}

          <Route
            path="/search"
            element={
              <SearchPage
                query={query}
                setQuery={setQuery}
                onSearch={onSearch}
                loading={loading}
                error={error}
              />
            }
          />


          {/* =================================================
              RESULTS
              ================================================= */}

          <Route
            path="/results"
            element={
              <ResultsPage
                results={results}
                loading={loading}
              />
            }
          />


          {/* =================================================
              SCENE
              ================================================= */}

          <Route
            path="/scene/:tileId"
            element={
              <SceneRoute
                results={results}
              />
            }
          />


          {/* =================================================
              CHANGES
              ================================================= */}

          <Route
            path="/changes"
            element={
              <ChangesPage />
            }
          />


          {/* =================================================
              REVIEW QUEUE
              ================================================= */}

          <Route
            path="/review"
            element={
              <ReviewPage />
            }
          />


          {/* =================================================
              REVIEW DETAIL
              ================================================= */}

          <Route
            path="/review/:tileId"
            element={
              <ReviewPage />
            }
          />


          {/* =================================================
              DATASET DETAIL
              ================================================= */}

          <Route
            path="/dataset/delhi_sentinel2"
            element={
              <DatasetDetailPage />
            }
          />


          {/* =================================================
              INCREMENTAL INGESTION
              ================================================= */}

          <Route
            path="/ingest"
            element={
              <IngestionPage />
            }
          />


          {/* =================================================
              DEFAULT
              ================================================= */}

          <Route
            path="*"
            element={
              <Navigate
                to="/search"
                replace
              />
            }
          />

        </Routes>

      </main>

    </div>
  );
}


/* ==========================================================
   SCENE ROUTE
   ========================================================== */

function SceneRoute({
  results,
}) {
  const location =
    useLocation();

  const navigate =
    useNavigate();

  const sceneFromState =
    location.state?.scene;

  const routeTileId =
    Number(
      location.pathname
        .split("/")
        .pop()
    );

  const scene =
    sceneFromState ||
    results.find(
      (item) =>
        item.eventTileId ===
        routeTileId
    );


  if (!scene) {

    return (
      <section
        className="
          orion-page
          page-message
        "
      >

        <p>
          SCENE DATA IS NOT
          AVAILABLE IN THE
          CURRENT SESSION.
        </p>


        <button
          onClick={() =>
            navigate(
              "/results"
            )
          }
        >
          ← BACK TO RESULTS
        </button>

      </section>
    );

  }


  return (
    <SceneDetail
      scene={scene}

      onBack={() =>
        navigate(
          "/results"
        )
      }
    />
  );
}


/* ==========================================================
   MAIN APP
   ========================================================== */

function App() {
  const [query, setQuery] =
    useState("");

  const [results, setResults] =
    useState([]);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");


  async function performSearch(
    searchQuery
  ) {
    const trimmedQuery =
      searchQuery.trim();

    if (!trimmedQuery) {
      return;
    }


    try {

      setLoading(true);

      setError("");


      const response =
        await fetch(
          `${API_BASE_URL}/search`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                query:
                  trimmedQuery,

                top_k: 5,
              }),
          }
        );


      if (!response.ok) {

        const errorText =
          await response.text();

        throw new Error(
          `HTTP ${response.status}: ${errorText}`
        );

      }


      const data =
        await response.json();


      console.log(
        "ORION semantic search response:",
        data
      );


      const searchResults =
        normalizeSearchResponse(
          data
        );


      console.log(
        "ORION normalized search results:",
        searchResults
      );


      const scenes =
        searchResults.map(
          resultToScene
        );


      console.log(
        "ORION scene results:",
        scenes
      );


      setResults(
        scenes
      );


    } catch (
      requestError
    ) {

      console.error(
        "ORION semantic search failed:",
        requestError
      );


      setResults([]);


      setError(
        "Semantic search failed. Check the backend terminal for details."
      );

    } finally {

      setLoading(false);

    }
  }


  return (
    <BrowserRouter>

      <AppLayout
        query={query}
        setQuery={setQuery}
        results={results}
        loading={loading}
        error={error}
        onSearch={
          performSearch
        }
      />

    </BrowserRouter>
  );
}


export default App;