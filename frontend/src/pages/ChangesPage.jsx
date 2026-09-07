import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE_URL = "http://127.0.0.1:8000";

/* ============================================================
   HELPERS
============================================================ */

function extractChangeEvents(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data?.events)) {
    return data.events;
  }

  if (Array.isArray(data?.change_events)) {
    return data.change_events;
  }

  if (Array.isArray(data?.results)) {
    return data.results;
  }

  if (Array.isArray(data?.data)) {
    return data.data;
  }

  if (Array.isArray(data?.items)) {
    return data.items;
  }

  return [];
}

function formatPercentage(value) {
  const number = Number(value ?? 0);

  if (!Number.isFinite(number)) {
    return "0.00%";
  }

  return `${number.toFixed(2)}%`;
}

function formatScore(value) {
  const number = Number(value ?? 0);

  if (!Number.isFinite(number)) {
    return "0.000";
  }

  return number.toFixed(3);
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  return String(value).slice(0, 10);
}

function getPriorityRank(priority) {
  const value = String(priority ?? "").toUpperCase();

  if (value === "HIGH") return 3;
  if (value === "MEDIUM") return 2;

  return 1;
}

function getDatasetName(event) {
  return (
    event?.dataset ??
    event?.dataset_id ??
    event?.scene_id ??
    "UNKNOWN DATASET"
  );
}

function getLocation(event) {
  if (
    typeof event?.location === "string" &&
    event.location.trim()
  ) {
    return event.location;
  }

  const dataset = getDatasetName(event);

  if (
    dataset === "jewar_airport_best" ||
    dataset === "jewar_airport"
  ) {
    return "Noida International Airport area, Jewar, Uttar Pradesh";
  }

  if (dataset === "prayagraj") {
    return "Prayagraj, Uttar Pradesh";
  }

  return "Satellite change event";
}

function getBeforeDate(event) {
  return (
    event?.before_date ??
    event?.before?.date ??
    event?.before?.observation ??
    "—"
  );
}

function getAfterDate(event) {
  return (
    event?.after_date ??
    event?.after?.date ??
    event?.after?.observation ??
    "—"
  );
}

function getSensor(event) {
  if (
    typeof event?.sensor === "string"
  ) {
    return event.sensor;
  }

  if (
    typeof event?.before?.sensor === "string"
  ) {
    return event.before.sensor;
  }

  if (
    typeof event?.after?.sensor === "string"
  ) {
    return event.after.sensor;
  }

  if (
    getDatasetName(event) ===
    "jewar_airport_best"
  ) {
    return "Copernicus Sentinel-2";
  }

  return "Satellite imagery";
}

function getResolution(event) {
  if (
    getDatasetName(event) ===
      "jewar_airport_best" ||
    getDatasetName(event) ===
      "jewar_airport"
  ) {
    return "10 m Sentinel-2 imagery";
  }

  if (
    typeof event?.resolution === "string"
  ) {
    return event.resolution;
  }

  return "256 × 256 tile";
}

function getEventLabel(event) {
  const id = Number(
    event?.tile_id ?? 0
  );

  const dataset =
    getDatasetName(event);

  if (
    dataset === "jewar_airport_best" ||
    dataset === "jewar_airport"
  ) {
    return `JEWAR EVENT ${id}`;
  }

  return `EVENT ${id}`;
}

function getEvidenceText(item) {
  if (
    typeof item === "string"
  ) {
    return item;
  }

  if (
    item &&
    typeof item === "object"
  ) {
    if (
      item.type &&
      item.path
    ) {
      return `${String(
        item.type
      )}: ${String(
        item.path
      )}`;
    }

    if (item.type) {
      return String(
        item.type
      );
    }

    if (item.path) {
      return String(
        item.path
      );
    }

    try {
      return JSON.stringify(
        item
      );
    } catch {
      return "Evidence signal";
    }
  }

  if (
    item === null ||
    item === undefined
  ) {
    return "";
  }

  return String(item);
}

function eventToScene(event) {
  const tileId = Number(
    event?.tile_id ?? 0
  );

  const x =
    event?.x ?? "—";

  const y =
    event?.y ?? "—";

  const dataset =
    getDatasetName(event);

  const beforeDate =
    getBeforeDate(event);

  const afterDate =
    getAfterDate(event);

  const isJewar =
    dataset ===
      "jewar_airport_best" ||
    dataset ===
      "jewar_airport";

  return {
    id:
      `ORION-CHANGE-${String(
        tileId
      ).padStart(3, "0")}`,

    tileId: isJewar
      ? `jewar_event_${tileId}`
      : `tile_${String(
          tileId
        ).padStart(
          5,
          "0"
        )}_x${x}_y${y}`,

    eventTileId:
      tileId,

    title: isJewar
      ? "Noida International Airport Area"
      : `Change Event ${tileId}`,

    rank: 1,

    match: Math.round(
      Number(
        event?.evidence_score ??
        0
      ) * 100
    ),

    score: Number(
      event?.evidence_score ??
      0
    ),

    location:
      getLocation(event),

    x: String(x),

    y: String(y),

    date:
      formatDate(
        afterDate
      ),

    beforeDate:
      formatDate(
        beforeDate
      ),

    sensor:
      getSensor(event),

    resolution:
      getResolution(event),

    changeType:
      event?.dominant_change_type ??
      "OTHER CHANGE",

    confidence:
      Math.round(
        Number(
          event?.evidence_score ??
          0
        ) * 100
      ),

    affectedArea:
      `${Number(
        event?.change_percentage ??
        0
      ).toFixed(2)}% CHANGE`,

    description:
      `Detected ${Number(
        event?.change_percentage ??
        0
      ).toFixed(2)}% pixel-level change between ${formatDate(
        beforeDate
      )} and ${formatDate(
        afterDate
      )}.`,

    tags: [
      "CHANGE EVENT",
      dataset,
      event?.priority ??
        "LOW",
      event?.evidence_confidence ??
        "LOW",
    ],

    filename:
      event?.before?.filename ??
      "",

    path:
      event?.before?.path ??
      "",

    sceneId:
      event?.scene_id ??
      (isJewar
        ? "jewar_airport"
        : "prayagraj"),

    observation:
      "before",

    sourceRaster:
      event?.source_raster ??
      event?.before?.source_raster ??
      "before.tif",

    tileSize:
      isJewar
        ? null
        : 256,

    rawResult:
      event,
  };
}

/* ============================================================
   MAIN PAGE
============================================================ */

export default function ChangesPage() {
  const navigate =
    useNavigate();

  const [events, setEvents] =
    useState([]);

  const [summary, setSummary] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [
    visibilityFilter,
    setVisibilityFilter,
  ] = useState("ACTIVE");

  const [
    priorityFilter,
    setPriorityFilter,
  ] = useState("ALL");

  const [
    confidenceFilter,
    setConfidenceFilter,
  ] = useState("ALL");

  const [
    typeFilter,
    setTypeFilter,
  ] = useState("ALL");

  const [
    datasetFilter,
    setDatasetFilter,
  ] = useState("ALL");

  const [
    sortMode,
    setSortMode,
  ] = useState("SEVERITY");

  /* ============================================================
     LOAD CHANGE EVENTS
  ============================================================ */

  useEffect(() => {
    let cancelled = false;

    async function loadChangeEvents() {
      try {
        setLoading(true);
        setError("");

        const [
          eventsResponse,
          summaryResponse,
        ] = await Promise.all([
          fetch(
            `${API_BASE_URL}/change-events?include_suppressed=true`
          ),
          fetch(
            `${API_BASE_URL}/change-events/summary`
          ),
        ]);

        if (
          !eventsResponse.ok
        ) {
          throw new Error(
            `Change events HTTP ${eventsResponse.status}`
          );
        }

        const eventsData =
          await eventsResponse.json();

        let summaryData =
          null;

        if (
          summaryResponse.ok
        ) {
          summaryData =
            await summaryResponse.json();
        }

        if (cancelled) {
          return;
        }

        const loadedEvents =
          extractChangeEvents(
            eventsData
          );

        setEvents(
          loadedEvents
        );

        setSummary(
          summaryData
        );

        console.log(
          "ORION change events loaded:",
          loadedEvents.length
        );

        console.log(
          "ORION change events:",
          loadedEvents
        );
      } catch (requestError) {
        console.error(
          "ORION change events failed:",
          requestError
        );

        if (!cancelled) {
          setEvents([]);
          setSummary(null);

          setError(
            "Change events could not be loaded. Check that the ORION backend is running."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadChangeEvents();

    return () => {
      cancelled = true;
    };
  }, []);

  /* ============================================================
     NORMALIZE EVENTS
  ============================================================ */

  const normalizedEvents =
    useMemo(() => {
      return events.map(
        (event) => ({
          ...event,

          numericTileId:
            Number(
              event?.tile_id ??
              -1
            ),

          changePercentage:
            Number(
              event?.change_percentage ??
              0
            ),

          severityScore:
            Number(
              event?.severity ??
              event?.severity_score ??
              event?.ranking?.severity ??
              event?.ranking?.severity_score ??
              0
            ),

          evidenceScore:
            Number(
              event?.evidence_score ??
              0
            ),

          dataset:
            getDatasetName(
              event
            ),

          beforeDate:
            getBeforeDate(
              event
            ),

          afterDate:
            getAfterDate(
              event
            ),

          displayLocation:
            getLocation(
              event
            ),
        })
      );
    }, [events]);

  /* ============================================================
     DATASET LIST
  ============================================================ */

  const datasets =
    useMemo(() => {
      return [
        ...new Set(
          normalizedEvents
            .map(
              (event) =>
                event?.dataset
            )
            .filter(Boolean)
        ),
      ].sort();
    }, [
      normalizedEvents,
    ]);

  /* ============================================================
     CHANGE TYPE LIST
  ============================================================ */

  const changeTypes =
    useMemo(() => {
      const types =
        normalizedEvents
          .map(
            (event) =>
              event?.dominant_change_type
          )
          .filter(Boolean);

      return [
        ...new Set(types),
      ].sort();
    }, [
      normalizedEvents,
    ]);

  /* ============================================================
     FILTER + SORT
  ============================================================ */

  const filteredEvents =
    useMemo(() => {
      const filtered =
        normalizedEvents.filter(
          (event) => {
            const priority =
              String(
                event?.priority ??
                ""
              ).toUpperCase();

            const confidence =
              String(
                event?.evidence_confidence ??
                ""
              ).toUpperCase();

            const changeType =
              String(
                event?.dominant_change_type ??
                ""
              ).toUpperCase();

            const dataset =
              String(
                event?.dataset ??
                ""
              );

            const suppressed =
              Boolean(
                event?.suppressed
              );

            if (
              visibilityFilter ===
                "ACTIVE" &&
              suppressed
            ) {
              return false;
            }

            if (
              visibilityFilter ===
                "SUPPRESSED" &&
              !suppressed
            ) {
              return false;
            }

            if (
              priorityFilter !==
                "ALL" &&
              priority !==
                priorityFilter
            ) {
              return false;
            }

            if (
              confidenceFilter !==
                "ALL" &&
              confidence !==
                confidenceFilter
            ) {
              return false;
            }

            if (
              typeFilter !==
                "ALL" &&
              changeType !==
                String(
                  typeFilter
                ).toUpperCase()
            ) {
              return false;
            }

            if (
              datasetFilter !==
                "ALL" &&
              dataset !==
                datasetFilter
            ) {
              return false;
            }

            return true;
          }
        );

      return filtered.sort(
        (a, b) => {
          /*
           * When a specific change type is selected,
           * rank the matching events by:
           *
           * 1. Priority
           * 2. Evidence strength
           * 3. Severity
           * 4. Change percentage
           *
           * This makes strong events such as
           * JEWAR EVENT 1000 rise to the top of
           * the ROAD DEVELOPMENT view.
           */
          if (typeFilter !== "ALL") {
            const priorityDifference =
              getPriorityRank(
                b.priority
              ) -
              getPriorityRank(
                a.priority
              );

            if (
              priorityDifference !== 0
            ) {
              return priorityDifference;
            }

            const evidenceDifference =
              b.evidenceScore -
              a.evidenceScore;

            if (
              evidenceDifference !== 0
            ) {
              return evidenceDifference;
            }

            const severityDifference =
              b.severityScore -
              a.severityScore;

            if (
              severityDifference !== 0
            ) {
              return severityDifference;
            }

            return (
              b.changePercentage -
              a.changePercentage
            );
          }

          if (
            sortMode ===
            "CHANGE"
          ) {
            return (
              b.changePercentage -
              a.changePercentage
            );
          }

          if (
            sortMode ===
            "CONFIDENCE"
          ) {
            return (
              b.evidenceScore -
              a.evidenceScore
            );
          }

          if (
            sortMode ===
            "PRIORITY"
          ) {
            return (
              getPriorityRank(
                b.priority
              ) -
              getPriorityRank(
                a.priority
              )
            );
          }

          return (
            b.severityScore -
            a.severityScore
          );
        }
      );
    }, [
      normalizedEvents,
      visibilityFilter,
      priorityFilter,
      confidenceFilter,
      typeFilter,
      datasetFilter,
      sortMode,
    ]);

  /* ============================================================
     SUMMARY VALUES
  ============================================================ */

  const totalEvents =
    summary?.total_events ??
    normalizedEvents.length;

  const activeEvents =
    summary?.active_events ??
    normalizedEvents.filter(
      (event) =>
        !event?.suppressed
    ).length;

  const suppressedEvents =
    summary?.suppressed_events ??
    normalizedEvents.filter(
      (event) =>
        Boolean(
          event?.suppressed
        )
    ).length;

  const highPriority =
    summary?.priority?.HIGH ??
    normalizedEvents.filter(
      (event) =>
        String(
          event?.priority ??
          ""
        ).toUpperCase() ===
        "HIGH"
    ).length;

  const highConfidence =
    summary?.confidence?.HIGH ??
    normalizedEvents.filter(
      (event) =>
        String(
          event?.evidence_confidence ??
          ""
        ).toUpperCase() ===
        "HIGH"
    ).length;

  /* ============================================================
     NAVIGATION
  ============================================================ */

  function openScene(event) {
    const scene =
      eventToScene(
        event
      );

    navigate(
      `/scene/${event.numericTileId}`,
      {
        state: {
          scene,
        },
      }
    );
  }

  function openReview(event) {
    navigate(
      `/review/${event.numericTileId}`
    );
  }

  function evidenceUrl(
    tileId,
    type
  ) {
    return (
      `${API_BASE_URL}/change-events/${tileId}/evidence/${type}?v=7`
    );
  }

  /* ============================================================
     LOADING
  ============================================================ */

  if (loading) {
    return (
      <section
        style={{
          padding:
            "40px 24px",
          maxWidth:
            "1500px",
          margin:
            "0 auto",
        }}
      >
        <div
          style={{
            border:
              "1px solid #e2e8f0",
            borderRadius:
              "14px",
            background:
              "#ffffff",
            padding:
              "60px",
            textAlign:
              "center",
          }}
        >
          <div
            style={{
              fontSize:
                "12px",
              fontWeight:
                800,
              letterSpacing:
                "0.12em",
              color:
                "#64748b",
            }}
          >
            LOADING CHANGE
            INTELLIGENCE
          </div>

          <div
            style={{
              marginTop:
                "8px",
              fontSize:
                "13px",
              color:
                "#94a3b8",
            }}
          >
            Retrieving
            detected
            change events...
          </div>
        </div>
      </section>
    );
  }

  /* ============================================================
     PAGE
  ============================================================ */

  return (
    <section
      style={{
        padding:
          "30px 24px 50px",
        maxWidth:
          "1500px",
        margin:
          "0 auto",
      }}
    >
      {/* HEADER */}

      <div
        style={{
          display:
            "flex",
          justifyContent:
            "space-between",
          alignItems:
            "flex-end",
          gap:
            "24px",
          marginBottom:
            "24px",
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
                "0.14em",
              color:
                "#64748b",
              marginBottom:
                "7px",
            }}
          >
            MULTI-TEMPORAL
            ANALYSIS
          </div>

          <h2
            style={{
              margin: 0,
              fontSize:
                "30px",
              letterSpacing:
                "-0.03em",
              color:
                "#0f172a",
            }}
          >
            Change
            Intelligence
          </h2>

          <p
            style={{
              margin:
                "8px 0 0",
              maxWidth:
                "850px",
              color:
                "#64748b",
              lineHeight:
                1.6,
              fontSize:
                "14px",
            }}
          >
            Review automatically
            detected temporal
            differences across
            indexed satellite
            imagery. Events are
            ranked using change
            severity and evidence
            signals.
          </p>
        </div>

        <div
          style={{
            padding:
              "10px 14px",
            border:
              "1px solid #dbe3ec",
            borderRadius:
              "10px",
            background:
              "#f8fafc",
            fontSize:
              "11px",
            fontWeight:
              800,
            letterSpacing:
              "0.08em",
            color:
              "#475569",
            whiteSpace:
              "nowrap",
          }}
        >
          {normalizedEvents.length}{" "}
          REGISTERED EVENTS
        </div>
      </div>

      {/* ERROR */}

      {error && (
        <div
          style={{
            marginBottom:
              "20px",
            padding:
              "14px 16px",
            border:
              "1px solid #fecaca",
            borderRadius:
              "10px",
            background:
              "#fff7f7",
            color:
              "#991b1b",
            fontSize:
              "13px",
          }}
        >
          {error}
        </div>
      )}

      {/* SUMMARY */}

      <div
        style={{
          display:
            "grid",
          gridTemplateColumns:
            "repeat(5, minmax(0, 1fr))",
          gap:
            "12px",
          marginBottom:
            "22px",
        }}
      >
        <SummaryCard
          label="TOTAL EVENTS"
          value={
            totalEvents
          }
          note="Registered change events"
        />

        <SummaryCard
          label="ACTIVE"
          value={
            activeEvents
          }
          note="Currently visible"
        />

        <SummaryCard
          label="SUPPRESSED"
          value={
            suppressedEvents
          }
          note="Filtered by quality logic"
        />

        <SummaryCard
          label="HIGH PRIORITY"
          value={
            highPriority
          }
          note="Requires attention"
        />

        <SummaryCard
          label="HIGH CONFIDENCE"
          value={
            highConfidence
          }
          note="Strongest evidence"
        />
      </div>

      {/* FILTERS */}

      <div
        style={{
          border:
            "1px solid #e2e8f0",
          borderRadius:
            "14px",
          background:
            "#ffffff",
          padding:
            "16px",
          marginBottom:
            "22px",
        }}
      >
        <div
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(6, minmax(0, 1fr))",
            gap:
              "12px",
          }}
        >
          <FilterControl
            label="VISIBILITY"
            value={
              visibilityFilter
            }
            onChange={
              setVisibilityFilter
            }
            options={[
              [
                "ACTIVE",
                "ACTIVE EVENTS",
              ],
              [
                "SUPPRESSED",
                "SUPPRESSED",
              ],
              [
                "ALL",
                "ALL EVENTS",
              ],
            ]}
          />

          <FilterControl
            label="DATASET"
            value={
              datasetFilter
            }
            onChange={
              setDatasetFilter
            }
            options={[
              [
                "ALL",
                "ALL DATASETS",
              ],
              ...datasets.map(
                (dataset) => [
                  dataset,
                  dataset,
                ]
              ),
            ]}
          />

          <FilterControl
            label="PRIORITY"
            value={
              priorityFilter
            }
            onChange={
              setPriorityFilter
            }
            options={[
              [
                "ALL",
                "ALL",
              ],
              [
                "HIGH",
                "HIGH",
              ],
              [
                "MEDIUM",
                "MEDIUM",
              ],
              [
                "LOW",
                "LOW",
              ],
            ]}
          />

          <FilterControl
            label="CONFIDENCE"
            value={
              confidenceFilter
            }
            onChange={
              setConfidenceFilter
            }
            options={[
              [
                "ALL",
                "ALL",
              ],
              [
                "HIGH",
                "HIGH",
              ],
              [
                "MEDIUM",
                "MEDIUM",
              ],
              [
                "LOW",
                "LOW",
              ],
            ]}
          />

          <FilterControl
            label="CHANGE TYPE"
            value={
              typeFilter
            }
            onChange={
              setTypeFilter
            }
            options={[
              [
                "ALL",
                "ALL TYPES",
              ],
              ...changeTypes.map(
                (type) => [
                  type,
                  type,
                ]
              ),
            ]}
          />

          <FilterControl
            label="SORT BY"
            value={
              sortMode
            }
            onChange={
              setSortMode
            }
            options={[
              [
                "SEVERITY",
                "SEVERITY",
              ],
              [
                "CHANGE",
                "CHANGE %",
              ],
              [
                "CONFIDENCE",
                "EVIDENCE",
              ],
              [
                "PRIORITY",
                "PRIORITY",
              ],
            ]}
          />
        </div>

        <div
          style={{
            marginTop:
              "12px",
            fontSize:
              "12px",
            color:
              "#64748b",
          }}
        >
          Showing{" "}
          <strong
            style={{
              color:
                "#0f172a",
            }}
          >
            {
              filteredEvents.length
            }
          </strong>{" "}
          of{" "}
          <strong
            style={{
              color:
                "#0f172a",
            }}
          >
            {
              events.length
            }
          </strong>{" "}
          registered
          events.
        </div>
      </div>

      {/* EVENTS */}

      {filteredEvents.length ===
      0 ? (
        <div
          style={{
            border:
              "1px solid #e2e8f0",
            borderRadius:
              "14px",
            background:
              "#ffffff",
            padding:
              "50px",
            textAlign:
              "center",
          }}
        >
          <div
            style={{
              fontSize:
                "13px",
              fontWeight:
                800,
              color:
                "#334155",
            }}
          >
            NO CHANGE EVENTS
            MATCH THE CURRENT
            FILTERS
          </div>

          <div
            style={{
              marginTop:
                "7px",
              fontSize:
                "12px",
              color:
                "#94a3b8",
            }}
          >
            Adjust the filters
            to display
            additional events.
          </div>
        </div>
      ) : (
        <div
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(430px, 1fr))",
            gap:
              "18px",
          }}
        >
          {filteredEvents.map(
            (event) => (
              <ChangeEventCard
                key={
                  event.numericTileId
                }
                event={
                  event
                }
                onOpenScene={() =>
                  openScene(
                    event
                  )
                }
                onOpenReview={() =>
                  openReview(
                    event
                  )
                }
                beforeUrl={evidenceUrl(
                  event.numericTileId,
                  "before"
                )}
                afterUrl={evidenceUrl(
                  event.numericTileId,
                  "after"
                )}
              />
            )
          )}
        </div>
      )}
    </section>
  );
}

/* ============================================================
   SUMMARY CARD
============================================================ */

function SummaryCard({
  label,
  value,
  note,
}) {
  return (
    <div
      style={{
        border:
          "1px solid #e2e8f0",
        borderRadius:
          "12px",
        background:
          "#ffffff",
        padding:
          "17px",
      }}
    >
      <div
        style={{
          fontSize:
            "10px",
          fontWeight:
            800,
          letterSpacing:
            "0.1em",
          color:
            "#64748b",
        }}
      >
        {label}
      </div>

      <div
        style={{
          marginTop:
            "8px",
          fontSize:
            "28px",
          fontWeight:
            800,
          lineHeight:
            1,
          color:
            "#0f172a",
        }}
      >
        {value}
      </div>

      <div
        style={{
          marginTop:
            "7px",
          fontSize:
            "11px",
          color:
            "#94a3b8",
        }}
      >
        {note}
      </div>
    </div>
  );
}

/* ============================================================
   FILTER CONTROL
============================================================ */

function FilterControl({
  label,
  value,
  onChange,
  options,
}) {
  return (
    <label
      style={{
        display:
          "flex",
        flexDirection:
          "column",
        gap:
          "6px",
      }}
    >
      <span
        style={{
          fontSize:
            "9px",
          fontWeight:
            800,
          letterSpacing:
            "0.1em",
          color:
            "#64748b",
        }}
      >
        {label}
      </span>

      <select
        value={
          value
        }
        onChange={(event) =>
          onChange(
            event.target.value
          )
        }
        style={{
          width:
            "100%",
          height:
            "38px",
          border:
            "1px solid #dbe3ec",
          borderRadius:
            "8px",
          padding:
            "0 10px",
          background:
            "#ffffff",
          color:
            "#0f172a",
          fontSize:
            "12px",
          fontWeight:
            700,
          outline:
            "none",
        }}
      >
        {options.map(
          ([
            optionValue,
            optionLabel,
          ]) => (
            <option
              key={
                optionValue
              }
              value={
                optionValue
              }
            >
              {
                optionLabel
              }
            </option>
          )
        )}
      </select>
    </label>
  );
}

/* ============================================================
   CHANGE EVENT CARD
============================================================ */

function ChangeEventCard({
  event,
  onOpenScene,
  onOpenReview,
  beforeUrl,
  afterUrl,
}) {
  const priority =
    String(
      event?.priority ??
      "LOW"
    ).toUpperCase();

  const confidence =
    String(
      event?.evidence_confidence ??
      "LOW"
    ).toUpperCase();

  const changeType =
    event?.dominant_change_type ??
    "OTHER CHANGE";

  const falseAlarmRisk =
    String(
      event?.false_alarm_risk ??
      "LOW"
    ).toUpperCase();

  const suppressed =
    Boolean(
      event?.suppressed
    );

  const dataset =
    event?.dataset ??
    event?.scene_id ??
    "UNKNOWN";

  const isJewar =
    dataset ===
      "jewar_airport_best" ||
    dataset ===
      "jewar_airport";

  return (
    <article
      style={{
        border:
          isJewar
            ? "2px solid #cbd5e1"
            : "1px solid #dfe6ee",
        borderRadius:
          "14px",
        background:
          "#ffffff",
        overflow:
          "hidden",
      }}
    >
      {/* HEADER */}

      <div
        style={{
          display:
            "flex",
          justifyContent:
            "space-between",
          alignItems:
            "center",
          gap:
            "12px",
          padding:
            "14px 16px",
          borderBottom:
            "1px solid #edf1f5",
        }}
      >
        <div>
          <div
            style={{
              fontSize:
                "10px",
              fontWeight:
                800,
              letterSpacing:
                "0.1em",
              color:
                "#64748b",
            }}
          >
            {isJewar
              ? "JEWAR CHANGE EVENT"
              : "DETECTED CHANGE EVENT"}
          </div>

          <div
            style={{
              marginTop:
                "4px",
              fontSize:
                "18px",
              fontWeight:
                800,
              color:
                "#0f172a",
            }}
          >
            {
              getEventLabel(
                event
              )
            }
          </div>

          <div
            style={{
              marginTop:
                "4px",
              fontSize:
                "10px",
              color:
                "#64748b",
            }}
          >
            {
              dataset
            }
          </div>
        </div>

        <div
          style={{
            display:
              "flex",
            gap:
              "6px",
          }}
        >
          <StatusBadge
            label={
              priority
            }
          />

          <StatusBadge
            label={
              confidence
            }
          />
        </div>
      </div>

      {/* BEFORE / AFTER */}

      <div
        style={{
          display:
            "grid",
          gridTemplateColumns:
            "1fr 1fr",
          gap:
            "1px",
          background:
            "#e2e8f0",
        }}
      >
        <EvidenceImage
          label={`BEFORE · ${formatDate(
            event.beforeDate
          )}`}
          src={
            beforeUrl
          }
        />

        <EvidenceImage
          label={`AFTER · ${formatDate(
            event.afterDate
          )}`}
          src={
            afterUrl
          }
        />
      </div>

      {/* DETAILS */}

      <div
        style={{
          padding:
            "16px",
        }}
      >
        {/* LOCATION */}

        <div
          style={{
            padding:
              "11px 12px",
            border:
              "1px solid #edf1f5",
            borderRadius:
              "8px",
            background:
              "#f8fafc",
            marginBottom:
              "14px",
          }}
        >
          <div
            style={{
              fontSize:
                "8px",
              fontWeight:
                800,
              letterSpacing:
                "0.08em",
              color:
                "#94a3b8",
              marginBottom:
                "4px",
            }}
          >
            LOCATION
          </div>

          <div
            style={{
              fontSize:
                "11px",
              fontWeight:
                700,
              color:
                "#334155",
            }}
          >
            {
              getLocation(
                event
              )
            }
          </div>
        </div>

        {/* METRICS */}

        <div
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
          <Metric
            label="CHANGE"
            value={formatPercentage(
              event.changePercentage
            )}
          />

          <Metric
            label="SEVERITY"
            value={formatScore(
              event.severityScore
            )}
          />

          <Metric
            label="EVIDENCE"
            value={formatScore(
              event.evidenceScore
            )}
          />
        </div>

        {/* INFORMATION */}

        <div
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "1fr 1fr",
            gap:
              "12px",
            marginBottom:
              "14px",
          }}
        >
          <InfoRow
            label="CHANGE TYPE"
            value={
              changeType
            }
          />

          <InfoRow
            label="FALSE-ALARM RISK"
            value={
              falseAlarmRisk
            }
          />

          <InfoRow
            label="BEFORE"
            value={formatDate(
              event.beforeDate
            )}
          />

          <InfoRow
            label="AFTER"
            value={formatDate(
              event.afterDate
            )}
          />

          <InfoRow
            label="SENSOR"
            value={
              getSensor(
                event
              )
            }
          />

          <InfoRow
            label="RESOLUTION"
            value={
              getResolution(
                event
              )
            }
          />

          <InfoRow
            label="REGIONS"
            value={String(
              event?.change_regions ??
              event?.regions ??
              0
            )}
          />

          <InfoRow
            label="CHANGED PIXELS"
            value={String(
              event?.changed_pixels ??
              0
            )}
          />
        </div>

        {/* EVENT LOCATION */}

        <div
          style={{
            padding:
              "11px 12px",
            border:
              "1px solid #edf1f5",
            borderRadius:
              "8px",
            background:
              "#f8fafc",
            marginBottom:
              "14px",
            fontSize:
              "11px",
            color:
              "#475569",
          }}
        >
          <strong
            style={{
              color:
                "#0f172a",
            }}
          >
            EVENT LOCATION
          </strong>

          <span>
            {" "}
            X:
            {
              event?.x ??
              "—"
            }{" "}
            · Y:
            {
              event?.y ??
              "—"
            }
          </span>
        </div>

        {/* EVIDENCE SIGNALS */}

        {Array.isArray(
          event?.evidence
        ) &&
          event.evidence.length >
            0 && (
            <div
              style={{
                marginBottom:
                  "14px",
              }}
            >
              <div
                style={{
                  fontSize:
                    "9px",
                  fontWeight:
                    800,
                  letterSpacing:
                    "0.1em",
                  color:
                    "#64748b",
                  marginBottom:
                    "7px",
                }}
              >
                EVIDENCE
                SIGNALS
              </div>

              {event.evidence
                .slice(
                  0,
                  4
                )
                .map(
                  (
                    item,
                    index
                  ) => {
                    const text =
                      getEvidenceText(
                        item
                      );

                    return (
                      <div
                        key={`${event.numericTileId}-${index}`}
                        style={{
                          fontSize:
                            "11px",
                          color:
                            "#475569",
                          marginBottom:
                            "5px",
                          wordBreak:
                            "break-word",
                        }}
                      >
                        •{" "}
                        {
                          text
                        }
                      </div>
                    );
                  }
                )}
            </div>
          )}

        {/* FOOTER */}

        <div
          style={{
            display:
              "flex",
            justifyContent:
              "space-between",
            alignItems:
              "center",
            gap:
              "10px",
          }}
        >
          <div
            style={{
              fontSize:
                "10px",
              fontWeight:
                700,
              color:
                suppressed
                  ? "#94a3b8"
                  : "#64748b",
            }}
          >
            {suppressed
              ? "SUPPRESSED EVENT"
              : "ACTIVE EVENT"}
          </div>

          <div
            style={{
              display:
                "flex",
              gap:
                "8px",
            }}
          >
            <button
              type="button"
              onClick={
                onOpenScene
              }
              style={{
                border:
                  "1px solid #cbd5e1",
                borderRadius:
                  "8px",
                padding:
                  "9px 13px",
                background:
                  "#ffffff",
                color:
                  "#0f172a",
                fontSize:
                  "10px",
                fontWeight:
                  800,
                letterSpacing:
                  "0.06em",
                cursor:
                  "pointer",
              }}
            >
              VIEW SCENE →
            </button>

            <button
              type="button"
              onClick={
                onOpenReview
              }
              style={{
                border:
                  "1px solid #cbd5e1",
                borderRadius:
                  "8px",
                padding:
                  "9px 13px",
                background:
                  "#0f172a",
                color:
                  "#ffffff",
                fontSize:
                  "10px",
                fontWeight:
                  800,
                letterSpacing:
                  "0.06em",
                cursor:
                  "pointer",
              }}
            >
              REVIEW →
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

/* ============================================================
   EVIDENCE IMAGE
============================================================ */

function EvidenceImage({
  label,
  src,
}) {
  const [failed, setFailed] =
    useState(false);

  useEffect(() => {
    setFailed(false);
  }, [src]);

  return (
    <div
      style={{
        position:
          "relative",
        minHeight:
          "190px",
        background:
          "#f1f5f9",
        overflow:
          "hidden",
      }}
    >
      {!failed ? (
        <img
          src={
            src
          }
          alt={`${label} satellite evidence`}
          onError={() =>
            setFailed(
              true
            )
          }
          style={{
            display:
              "block",
            width:
              "100%",
            height:
              "100%",
            minHeight:
              "190px",
            objectFit:
              "cover",
          }}
        />
      ) : (
        <div
          style={{
            minHeight:
              "190px",
            display:
              "flex",
            alignItems:
              "center",
            justifyContent:
              "center",
            padding:
              "20px",
            textAlign:
              "center",
            color:
              "#94a3b8",
            fontSize:
              "11px",
          }}
        >
          <span>
            {label}
            <br />
            EVIDENCE
            UNAVAILABLE
          </span>
        </div>
      )}

      <div
        style={{
          position:
            "absolute",
          top:
            "9px",
          left:
            "9px",
          padding:
            "5px 7px",
          borderRadius:
            "5px",
          background:
            "rgba(255,255,255,0.94)",
          color:
            "#334155",
          fontSize:
            "9px",
          fontWeight:
            800,
          letterSpacing:
            "0.08em",
        }}
      >
        {label}
      </div>
    </div>
  );
}

/* ============================================================
   METRIC
============================================================ */

function Metric({
  label,
  value,
}) {
  return (
    <div
      style={{
        padding:
          "10px",
        border:
          "1px solid #edf1f5",
        borderRadius:
          "8px",
        background:
          "#fbfdff",
      }}
    >
      <div
        style={{
          fontSize:
            "8px",
          fontWeight:
            800,
          letterSpacing:
            "0.08em",
          color:
            "#94a3b8",
        }}
      >
        {label}
      </div>

      <div
        style={{
          marginTop:
            "5px",
          fontSize:
            "15px",
          fontWeight:
            800,
          color:
            "#0f172a",
        }}
      >
        {value}
      </div>
    </div>
  );
}

/* ============================================================
   INFO ROW
============================================================ */

function InfoRow({
  label,
  value,
}) {
  return (
    <div>
      <div
        style={{
          fontSize:
            "8px",
          fontWeight:
            800,
          letterSpacing:
            "0.08em",
          color:
            "#94a3b8",
          marginBottom:
            "4px",
        }}
      >
        {label}
      </div>

      <div
        style={{
          fontSize:
            "11px",
          fontWeight:
            700,
          color:
            "#334155",
          wordBreak:
            "break-word",
        }}
      >
        {String(
          value ??
          "—"
        )}
      </div>
    </div>
  );
}

/* ============================================================
   STATUS BADGE
============================================================ */

function StatusBadge({
  label,
}) {
  let background =
    "#f8fafc";

  let color =
    "#64748b";

  let border =
    "#e2e8f0";

  if (
    label ===
    "HIGH"
  ) {
    background =
      "#fff7ed";

    color =
      "#c2410c";

    border =
      "#fed7aa";
  }

  if (
    label ===
    "MEDIUM"
  ) {
    background =
      "#fefce8";

    color =
      "#a16207";

    border =
      "#fde68a";
  }

  return (
    <span
      style={{
        display:
          "inline-flex",
        alignItems:
          "center",
        padding:
          "5px 7px",
        border:
          `1px solid ${border}`,
        borderRadius:
          "5px",
        background,
        color,
        fontSize:
          "8px",
        fontWeight:
          800,
        letterSpacing:
          "0.06em",
      }}
    >
      {label}
    </span>
  );
}