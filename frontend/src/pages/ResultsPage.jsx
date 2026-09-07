import { useNavigate } from "react-router-dom";

const API_BASE_URL =
  "http://127.0.0.1:8000";

/*
 * ============================================================
 * RESULTS PAGE
 * ============================================================
 *
 * This page displays semantic search results.
 *
 * Special handling:
 *
 * Prayagraj:
 *   Uses the normal numeric event/tile ID.
 *
 * Jewar:
 *   The search index contains:
 *   jewar_airport_before
 *   jewar_airport_after
 *
 *   These are full-AOI search records and do not have a
 *   normal Prayagraj tile ID.
 *
 *   Jewar has already been registered as change Event 1000,
 *   so the result is connected to Event 1000 for:
 *
 *   - before image
 *   - after image
 *   - change mask
 *   - scene details
 *
 * ============================================================
 */


/* ============================================================
   HELPER: DETECT JEWAR RESULT
   ============================================================ */

function isJewarScene(scene) {
  const dataset = String(
    scene?.dataset ??
      scene?.dataset_id ??
      ""
  ).toLowerCase();

  const tileId = String(
    scene?.tileId ??
      scene?.tile_id ??
      ""
  ).toLowerCase();

  const filename = String(
    scene?.filename ??
      ""
  ).toLowerCase();

  return (
    dataset === "jewar_airport_best" ||
    dataset === "jewar_airport" ||
    tileId.includes("jewar_airport") ||
    filename.includes("jewar_airport")
  );
}


/* ============================================================
   HELPER: GET NUMERIC EVENT ID
   ============================================================ */

function getEventTileId(scene) {
  /*
   * If the result already has a numeric eventTileId,
   * use it directly.
   */

  if (
    scene?.eventTileId !== null &&
    scene?.eventTileId !== undefined &&
    Number.isFinite(
      Number(scene.eventTileId)
    )
  ) {
    return Number(
      scene.eventTileId
    );
  }

  /*
   * Jewar is registered as Event 1000.
   */

  if (isJewarScene(scene)) {
    return 1000;
  }

  return null;
}


/* ============================================================
   HELPER: GET THUMBNAIL URL
   ============================================================ */

function getThumbnailUrl(scene) {
  const eventTileId =
    getEventTileId(scene);

  if (
    eventTileId === null ||
    eventTileId === undefined
  ) {
    return "";
  }

  /*
   * For Jewar search results we show the AFTER image,
   * because the current indexed result is
   * jewar_airport_after.
   *
   * For normal Prayagraj results we retain the existing
   * BEFORE evidence behavior.
   */

  const evidenceType =
    isJewarScene(scene)
      ? "after"
      : "before";

  return (
    `${API_BASE_URL}/change-events/` +
    `${eventTileId}/evidence/` +
    `${evidenceType}?v=10`
  );
}


/* ============================================================
   HELPER: OPEN SCENE
   ============================================================ */

function prepareSceneForDetails(scene) {
  const eventTileId =
    getEventTileId(scene);

  /*
   * Nothing to prepare for an ordinary result that
   * has no registered change event.
   */

  if (
    eventTileId === null ||
    eventTileId === undefined
  ) {
    return null;
  }

  /*
   * Jewar does not use the normal:
   *
   * tile_00029_x1792_y512
   *
   * naming scheme.
   *
   * SceneDetail currently extracts the numeric ID from
   * the tileId string, so we provide a small compatible
   * route identifier while preserving the original
   * Jewar tile name in originalTileId.
   */

  if (isJewarScene(scene)) {
    return {
      ...scene,

      eventTileId: 1000,

      tileId:
        "tile_01000_x0_y0",

      originalTileId:
        scene.tileId ??
        "jewar_airport_after",

      id:
        scene.id ??
        "ORION-TILE-001",

      title:
        "Noida International Airport Area",

      location:
        scene.location ??
        "Noida International Airport area, Jewar, Uttar Pradesh",

      dataset:
        scene.dataset ??
        "jewar_airport_best",

      sensor:
        scene.sensor ??
        "Copernicus Sentinel-2",

      resolution:
        scene.resolution ??
        "10 m Sentinel-2 imagery",

      changeType:
        scene.changeType ??
        "ROAD DEVELOPMENT",

      beforeDate:
        scene.beforeDate ??
        "2022-12-10",

      date:
        scene.date ??
        "2023-10-06",

      observation:
        scene.observation ??
        "after",

      sceneId:
        scene.sceneId ??
        "jewar_airport_best",

      sourceRaster:
        scene.sourceRaster ??
        "B04.tif",

      tileSize:
        scene.tileSize ??
        145,

      /*
       * Keep the original search result available.
       */

      rawSearchResult:
        scene.rawSearchResult ??
        scene,
    };
  }

  /*
   * Normal Prayagraj scene.
   */

  return {
    ...scene,
    eventTileId,
  };
}


/* ============================================================
   MAIN COMPONENT
   ============================================================ */

function ResultsPage({
  results,
  loading,
}) {
  const navigate =
    useNavigate();


  /* ==========================================================
     OPEN SCENE
     ========================================================== */

  function openScene(scene) {
    const eventTileId =
      getEventTileId(scene);

    /*
     * If there is no registered event, do not navigate
     * to a broken scene.
     */

    if (
      eventTileId === null ||
      eventTileId === undefined
    ) {
      console.warn(
        "ORION: No registered event for search result:",
        scene
      );

      return;
    }

    const detailScene =
      prepareSceneForDetails(
        scene
      );

    if (!detailScene) {
      return;
    }

    /*
     * Navigate using the real event ID.
     *
     * For Jewar this becomes:
     *
     * /scene/1000
     */

    navigate(
      `/scene/${eventTileId}`,
      {
        state: {
          scene:
            detailScene,
        },
      }
    );
  }


  /* ==========================================================
     SAFE RESULTS ARRAY
     ========================================================== */

  const safeResults =
    Array.isArray(results)
      ? results
      : [];


  /* ==========================================================
     RENDER
     ========================================================== */

  return (
    <section className="results-section">

      {/* ======================================================
          HEADER
          ====================================================== */}

      <div className="results-header">

        <div>

          <span className="section-label">
            02 / RETRIEVAL RESULTS
          </span>

          <h3>

            MATCHED

            <br />

            <span>
              SCENES.
            </span>

          </h3>

        </div>

        <div className="result-count">

          {loading
            ? "SEARCHING..."
            : `${safeResults.length} SCENES FOUND`}

        </div>

      </div>


      {/* ======================================================
          LOADING
          ====================================================== */}

      {loading ? (

        <div
          style={{
            padding: "60px 20px",
            textAlign: "center",
          }}
        >

          RUNNING REMOTECLIP

          <br />

          SEMANTIC SATELLITE SEARCH...

        </div>

      ) : safeResults.length === 0 ? (

        /* ====================================================
           EMPTY
           ==================================================== */

        <div
          style={{
            padding: "60px 20px",
            textAlign: "center",
          }}
        >

          NO MATCHING SCENES FOUND.

        </div>

      ) : (

        /* ====================================================
           RESULTS
           ==================================================== */

        <div className="results-grid">

          {safeResults.map(
            (scene, index) => {

              const thumbnailUrl =
                getThumbnailUrl(
                  scene
                );

              const eventTileId =
                getEventTileId(
                  scene
                );

              const jewar =
                isJewarScene(
                  scene
                );


              /*
               * Retrieval score is a similarity score.
               *
               * It is NOT:
               * - probability
               * - accuracy
               * - model confidence
               *
               * Therefore we show the raw score instead of
               * converting 0.2897 into a misleading "29%".
               */

              const numericScore =
                Number(
                  scene?.score ?? 0
                );

              const safeScore =
                Number.isFinite(
                  numericScore
                )
                  ? numericScore
                  : 0;


              /*
               * Safe tags.
               */

              const tags =
                Array.isArray(
                  scene?.tags
                )
                  ? scene.tags
                  : [];


              return (

                <article
                  className="scene-card"
                  key={
                    `${scene?.tileId ?? "scene"}-${index}`
                  }
                >

                  {/* =================================================
                      CARD HEADER
                      ================================================= */}

                  <div className="scene-top">

                    <span className="scene-rank">

                      #
                      {String(
                        index + 1
                      ).padStart(
                        2,
                        "0"
                      )}

                    </span>


                    <span
                      className="match-score"
                      title="RemoteCLIP semantic retrieval similarity score"
                    >

                      {safeScore.toFixed(
                        3
                      )}

                      {" "}

                      SCORE

                    </span>

                  </div>


                  {/* =================================================
                      IMAGE
                      ================================================= */}

                  <div className="scene-image">

                    {thumbnailUrl ? (

                      <img
                        src={thumbnailUrl}
                        alt={
                          jewar
                            ? "Noida International Airport Area satellite imagery"
                            : `Satellite tile ${scene?.tileId ?? ""}`
                        }
                        className="real-result-thumbnail"
                        onError={(
                          event
                        ) => {

                          /*
                           * Hide broken image and show a clear
                           * fallback instead of a broken-image icon.
                           */

                          event.currentTarget.style.display =
                            "none";

                          const parent =
                            event.currentTarget
                              .parentElement;

                          if (
                            parent &&
                            !parent.querySelector(
                              ".result-image-fallback"
                            )
                          ) {

                            const fallback =
                              document.createElement(
                                "div"
                              );

                            fallback.className =
                              "image-placeholder result-image-fallback";

                            fallback.innerHTML =
                              "SATELLITE<br />IMAGE UNAVAILABLE";

                            parent.appendChild(
                              fallback
                            );
                          }

                        }}
                      />

                    ) : (

                      <div className="image-placeholder">

                        SATELLITE

                        <br />

                        TILE{" "}

                        {scene?.tileId ??
                          "UNKNOWN"}

                      </div>

                    )}


                    <span className="scene-id">

                      {scene?.id ??
                        `ORION-TILE-${String(
                          index + 1
                        ).padStart(
                          3,
                          "0"
                        )}`}

                    </span>

                  </div>


                  {/* =================================================
                      CONTENT
                      ================================================= */}

                  <div className="scene-content">

                    <h4>

                      {scene?.title ??
                        "Satellite Scene"}

                    </h4>


                    <p className="scene-description">

                      {scene?.description ??
                        "Semantic retrieval matched this satellite scene to the submitted query."}

                    </p>


                    {/* =================================================
                        METADATA
                        ================================================= */}

                    <div className="scene-meta">

                      {/* TILE */}

                      <div>

                        <span>
                          TILE
                        </span>

                        <strong>

                          {scene?.tileId ??
                            "—"}

                        </strong>

                      </div>


                      {/* X */}

                      <div>

                        <span>
                          X COORDINATE
                        </span>

                        <strong>

                          {scene?.x ??
                            "—"}

                        </strong>

                      </div>


                      {/* Y */}

                      <div>

                        <span>
                          Y COORDINATE
                        </span>

                        <strong>

                          {scene?.y ??
                            "—"}

                        </strong>

                      </div>


                      {/* SCORE */}

                      <div>

                        <span>
                          RETRIEVAL SCORE
                        </span>

                        <strong>

                          {safeScore.toFixed(
                            4
                          )}

                        </strong>

                      </div>

                    </div>


                    {/* =================================================
                        EXTRA JEWAR INFORMATION
                        ================================================= */}

                    {jewar && (

                      <div
                        style={{
                          marginTop: "10px",
                          padding:
                            "9px 11px",
                          border:
                            "1px solid #dbe3ec",
                          background:
                            "#f8fafc",
                          borderRadius:
                            "7px",
                          fontSize:
                            "10px",
                          lineHeight:
                            1.5,
                          color:
                            "#64748b",
                        }}
                      >

                        <strong
                          style={{
                            color:
                              "#334155",
                          }}
                        >
                          JEWAR DATASET
                        </strong>

                        <br />

                        Sentinel-2 ·
                        2022-12-10 →
                        2023-10-06 ·
                        Change Event 1000

                      </div>

                    )}


                    {/* =================================================
                        FOOTER
                        ================================================= */}

                    <div className="scene-footer">

                      {/* TAGS */}

                      <div className="tags">

                        {tags.length >
                        0 ? (

                          tags.map(
                            (
                              tag,
                              tagIndex
                            ) => (

                              <span
                                key={`${tag}-${tagIndex}`}
                              >
                                {String(
                                  tag
                                )}
                              </span>

                            )
                          )

                        ) : (

                          <span>
                            SEMANTIC MATCH
                          </span>

                        )}

                      </div>


                      {/* VIEW DETAILS */}

                      <button
                        type="button"
                        disabled={
                          eventTileId ===
                            null ||
                          eventTileId ===
                            undefined
                        }
                        onClick={() =>
                          openScene(
                            scene
                          )
                        }
                        style={{
                          cursor:
                            eventTileId ===
                              null ||
                            eventTileId ===
                              undefined
                              ? "not-allowed"
                              : "pointer",
                          opacity:
                            eventTileId ===
                              null ||
                            eventTileId ===
                              undefined
                              ? 0.5
                              : 1,
                        }}
                      >

                        VIEW DETAILS →

                      </button>

                    </div>

                  </div>

                </article>

              );
            }
          )}

        </div>

      )}

    </section>
  );
}


export default ResultsPage;