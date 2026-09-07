import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

const API_BASE_URL = "http://127.0.0.1:8000";

/* ============================================================
   HELPERS
============================================================ */

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

function safeText(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  if (
    typeof value === "string" ||
    typeof value === "number"
  ) {
    return String(value);
  }

  if (typeof value === "object") {
    if (
      value.type &&
      value.path
    ) {
      return `${String(value.type)}: ${String(value.path)}`;
    }

    if (value.type) {
      return String(value.type);
    }

    if (value.path) {
      return String(value.path);
    }

    try {
      return JSON.stringify(value);
    } catch {
      return "[object]";
    }
  }

  return String(value);
}

function evidenceText(item) {
  if (typeof item === "string") {
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
      return `${String(item.type).toUpperCase()}: ${String(item.path)}`;
    }

    if (item.type) {
      return String(item.type).toUpperCase();
    }

    if (item.path) {
      return String(item.path);
    }

    try {
      return JSON.stringify(item);
    } catch {
      return "[EVIDENCE OBJECT]";
    }
  }

  return String(item ?? "");
}

function isJewarEvent(event) {
  const dataset =
    event?.dataset ??
    "";

  const sceneId =
    event?.scene_id ??
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

function getDatasetLabel(event) {
  if (isJewarEvent(event)) {
    return "JEWAR AIRPORT";
  }

  return String(
    event?.dataset ??
      event?.scene_id ??
      "PRAYAGRAJ"
  )
    .replaceAll("_", " ")
    .toUpperCase();
}

function getLocationLabel(event) {
  if (event?.location) {
    return String(
      event.location
    );
  }

  if (isJewarEvent(event)) {
    return "Noida International Airport area, Jewar, Uttar Pradesh";
  }

  return "Prayagraj, Uttar Pradesh";
}

function getSensorLabel(event) {
  return (
    event?.sensor ??
    event?.before?.sensor ??
    event?.after?.sensor ??
    (isJewarEvent(event)
      ? "Copernicus Sentinel-2"
      : "Satellite imagery")
  );
}

function getProductLabel(event) {
  return (
    event?.product ??
    event?.before?.product ??
    event?.after?.product ??
    (isJewarEvent(event)
      ? "Sentinel-2 Level-2A Surface Reflectance"
      : "RGB satellite imagery")
  );
}

function getResolutionLabel(event) {
  if (isJewarEvent(event)) {
    return "10 m";
  }

  return (
    event?.resolution ??
    "256 × 256 tile"
  );
}

function getMGRSLabel(event) {
  return (
    event?.mgrs_tile ??
    "—"
  );
}

function getCRSLabel(event) {
  return (
    event?.source_crs ??
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

function StatusBadge({ label }) {
  const value =
    String(
      label ?? "LOW"
    ).toUpperCase();

  let background =
    "#f8fafc";

  let color =
    "#64748b";

  let border =
    "#e2e8f0";

  if (value === "HIGH") {
    background =
      "#fff7ed";
    color =
      "#c2410c";
    border =
      "#fed7aa";
  }

  if (value === "MEDIUM") {
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
          "6px 9px",
        border:
          `1px solid ${border}`,
        borderRadius:
          "6px",
        background,
        color,
        fontSize:
          "9px",
        fontWeight:
          800,
        letterSpacing:
          "0.07em",
      }}
    >
      {value}
    </span>
  );
}

function DecisionBadge({ decision }) {
  const value =
    String(
      decision ?? ""
    ).toUpperCase();

  const confirmed =
    value ===
    "CONFIRMED";

  return (
    <span
      style={{
        display:
          "inline-flex",
        alignItems:
          "center",
        padding:
          "6px 9px",
        border:
          confirmed
            ? "1px solid #bbf7d0"
            : "1px solid #fecaca",
        borderRadius:
          "6px",
        background:
          confirmed
            ? "#f0fdf4"
            : "#fef2f2",
        color:
          confirmed
            ? "#166534"
            : "#991b1b",
        fontSize:
          "9px",
        fontWeight:
          800,
        letterSpacing:
          "0.07em",
      }}
    >
      {value}
    </span>
  );
}

function MetricCard({
  label,
  value,
}) {
  return (
    <div
      style={{
        border:
          "1px solid #e2e8f0",
        borderRadius:
          "10px",
        background:
          "#ffffff",
        padding:
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
            "0.09em",
          color:
            "#94a3b8",
        }}
      >
        {label}
      </div>

      <div
        style={{
          marginTop:
            "6px",
          fontSize:
            "16px",
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

function InfoItem({
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
            "12px",
          fontWeight:
            700,
          color:
            "#334155",
          wordBreak:
            "break-word",
        }}
      >
        {safeText(value)}
      </div>
    </div>
  );
}

function EvidencePanel({
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
          "360px",
        background:
          "#f1f5f9",
        overflow:
          "hidden",
        borderRadius:
          "10px",
      }}
    >
      {!failed &&
      src ? (
        <img
          src={src}
          alt={`${label} satellite evidence`}
          onError={() =>
            setFailed(true)
          }
          style={{
            display:
              "block",
            width:
              "100%",
            height:
              "360px",
            objectFit:
              "cover",
          }}
        />
      ) : (
        <div
          style={{
            height:
              "360px",
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
              "12px",
          }}
        >
          {label}
          <br />
          EVIDENCE UNAVAILABLE
        </div>
      )}

      <div
        style={{
          position:
            "absolute",
          top:
            "12px",
          left:
            "12px",
          padding:
            "6px 8px",
          borderRadius:
            "5px",
          background:
            "rgba(255,255,255,0.95)",
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

function extractEvents(data) {
  if (Array.isArray(data)) {
    return data;
  }

  if (
    Array.isArray(
      data?.events
    )
  ) {
    return data.events;
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
      data?.data
    )
  ) {
    return data.data;
  }

  return [];
}

function latestReviewsByTile(
  auditData
) {
  const reviews =
    Array.isArray(
      auditData?.reviews
    )
      ? auditData.reviews
      : [];

  const latest = {};

  for (
    const item of reviews
  ) {
    const tile =
      Number(
        item?.tile_id
      );

    if (
      !Number.isFinite(
        tile
      )
    ) {
      continue;
    }

    const previous =
      latest[tile];

    if (
      !previous ||
      String(
        item?.reviewed_at ??
          ""
      ) >
        String(
          previous?.reviewed_at ??
            ""
        )
    ) {
      latest[tile] =
        item;
    }
  }

  return latest;
}

function QueueStatusBadge({
  label,
  tone = "neutral",
}) {
  const styles = {
    neutral: {
      background:
        "#f8fafc",
      color:
        "#475569",
      border:
        "#e2e8f0",
    },

    green: {
      background:
        "#f0fdf4",
      color:
        "#166534",
      border:
        "#bbf7d0",
    },

    red: {
      background:
        "#fef2f2",
      color:
        "#991b1b",
      border:
        "#fecaca",
    },

    amber: {
      background:
        "#fffbeb",
      color:
        "#92400e",
      border:
        "#fde68a",
    },
  };

  const style =
    styles[tone] ??
    styles.neutral;

  return (
    <span
      style={{
        display:
          "inline-flex",
        alignItems:
          "center",
        padding:
          "5px 8px",
        border:
          `1px solid ${style.border}`,
        borderRadius:
          "6px",
        background:
          style.background,
        color:
          style.color,
        fontSize:
          "8px",
        fontWeight:
          800,
        letterSpacing:
          "0.07em",
      }}
    >
      {label}
    </span>
  );
}

/* ============================================================
   REVIEW QUEUE
============================================================ */

function ReviewQueuePage() {
  const navigate =
    useNavigate();

  const [events, setEvents] =
    useState([]);

  const [reviews, setReviews] =
    useState({});

  const [summary, setSummary] =
    useState(null);

  const [filter, setFilter] =
    useState("NEEDS REVIEW");

  const [priorityFilter, setPriorityFilter] =
    useState("ALL");

  const [typeFilter, setTypeFilter] =
    useState("ALL");

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  async function loadQueue() {
    try {
      setLoading(true);
      setError("");

      const [
        eventsResponse,
        summaryResponse,
        auditResponse,
      ] =
        await Promise.all([
          fetch(
            `${API_BASE_URL}/change-events`
          ),

          fetch(
            `${API_BASE_URL}/change-events/summary`
          ),

          fetch(
            `${API_BASE_URL}/review-audit`
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

      const summaryData =
        summaryResponse.ok
          ? await summaryResponse.json()
          : null;

      const auditData =
        auditResponse.ok
          ? await auditResponse.json()
          : null;

      setEvents(
        extractEvents(
          eventsData
        )
      );

      setSummary(
        summaryData
      );

      setReviews(
        latestReviewsByTile(
          auditData
        )
      );
    } catch (
      requestError
    ) {
      console.error(
        "ORION review queue failed:",
        requestError
      );

      setError(
        "Review queue could not be loaded. Check the ORION backend."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadQueue();
  }, []);

  const visibleEvents =
    events
      .filter(
        (event) =>
          !event?.suppressed
      )
      .filter(
        (event) => {
          const tile =
            Number(
              event?.tile_id
            );

          const review =
            reviews[tile];

          if (
            filter ===
            "NEEDS REVIEW"
          ) {
            return !review;
          }

          if (
            filter ===
            "CONFIRMED"
          ) {
            return (
              review?.decision ===
              "CONFIRMED"
            );
          }

          if (
            filter ===
            "REJECTED"
          ) {
            return (
              review?.decision ===
              "REJECTED"
            );
          }

          return true;
        }
      )
      .filter(
        (event) => {
          if (
            priorityFilter ===
            "ALL"
          ) {
            return true;
          }

          return (
            String(
              event?.priority ??
                "LOW"
            ).toUpperCase() ===
            priorityFilter
          );
        }
      )
      .filter(
        (event) => {
          if (
            typeFilter ===
            "ALL"
          ) {
            return true;
          }

          return (
            String(
              event?.dominant_change_type ??
                "OTHER CHANGE"
            ).toUpperCase() ===
            typeFilter
          );
        }
      )
      .sort(
        (a, b) => {
          const aReviewed =
            Boolean(
              reviews[
                Number(
                  a?.tile_id
                )
              ]
            );

          const bReviewed =
            Boolean(
              reviews[
                Number(
                  b?.tile_id
                )
              ]
            );

          if (
            aReviewed !==
            bReviewed
          ) {
            return aReviewed
              ? 1
              : -1;
          }

          return (
            Number(
              b?.evidence_score ??
                0
            ) -
            Number(
              a?.evidence_score ??
                0
            )
          );
        }
      );

  if (loading) {
    return (
      <section
        style={{
          padding:
            "40px 24px 70px",
          maxWidth:
            "1450px",
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
              "70px 30px",
            textAlign:
              "center",
          }}
        >
          <div
            style={{
              fontSize:
                "11px",
              fontWeight:
                800,
              letterSpacing:
                "0.14em",
              color:
                "#64748b",
            }}
          >
            LOADING ANALYST REVIEW QUEUE
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
            Loading active change events and review history...
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section
        style={{
          padding:
            "40px 24px 70px",
          maxWidth:
            "1450px",
          margin:
            "0 auto",
        }}
      >
        <div
          style={{
            border:
              "1px solid #fecaca",
            borderRadius:
              "14px",
            background:
              "#fff7f7",
            padding:
              "40px",
          }}
        >
          <div
            style={{
              fontSize:
                "13px",
              fontWeight:
                800,
              color:
                "#991b1b",
            }}
          >
            REVIEW QUEUE UNAVAILABLE
          </div>

          <p
            style={{
              margin:
                "8px 0 0",
              color:
                "#7f1d1d",
              fontSize:
                "12px",
            }}
          >
            {error}
          </p>

          <button
            type="button"
            onClick={
              loadQueue
            }
            style={{
              marginTop:
                "18px",
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
              cursor:
                "pointer",
            }}
          >
            RETRY
          </button>
        </div>
      </section>
    );
  }

  const activeCount =
    Number(
      summary?.active_events ??
        0
    );

  const suppressedCount =
    Number(
      summary?.suppressed_events ??
        0
    );

  const needsReviewCount =
    events.filter(
      (event) =>
        !event?.suppressed &&
        !reviews[
          Number(
            event?.tile_id
          )
        ]
    ).length;

  return (
    <section
      style={{
        padding:
          "30px 24px 65px",
        maxWidth:
          "1450px",
        margin:
          "0 auto",
      }}
    >
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
                "11px",
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
            ANALYST WORKFLOW
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
            Change Review Queue
          </h2>

          <p
            style={{
              margin:
                "8px 0 0",
              color:
                "#64748b",
              fontSize:
                "14px",
              lineHeight:
                1.6,
              maxWidth:
                "760px",
            }}
          >
            Review active automated detections using before-and-after evidence, model confidence, priority and change classification.
          </p>
        </div>

        <button
          type="button"
          onClick={
            loadQueue
          }
          style={{
            border:
              "1px solid #cbd5e1",
            borderRadius:
              "8px",
            padding:
              "10px 14px",
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
          ↻ REFRESH QUEUE
        </button>
      </div>

      <div
        style={{
          display:
            "grid",
          gridTemplateColumns:
            "repeat(4, minmax(0, 1fr))",
          gap:
            "10px",
          marginBottom:
            "18px",
        }}
      >
        <MetricCard
          label="ACTIVE EVENTS"
          value={
            activeCount
          }
        />

        <MetricCard
          label="NEEDS REVIEW"
          value={
            needsReviewCount
          }
        />

        <MetricCard
          label="SUPPRESSED"
          value={
            suppressedCount
          }
        />

        <MetricCard
          label="VISIBLE IN QUEUE"
          value={
            visibleEvents.length
          }
        />
      </div>

      <div
        style={{
          display:
            "grid",
          gridTemplateColumns:
            "minmax(0, 1fr) 180px 210px",
          gap:
            "10px",
          marginBottom:
            "20px",
        }}
      >
        <div
          style={{
            display:
              "flex",
            flexWrap:
              "wrap",
            gap:
              "7px",
            padding:
              "7px",
            border:
              "1px solid #e2e8f0",
            borderRadius:
              "10px",
            background:
              "#f8fafc",
          }}
        >
          {[
            "NEEDS REVIEW",
            "ALL",
            "CONFIRMED",
            "REJECTED",
          ].map(
            (item) => (
              <button
                key={
                  item
                }
                type="button"
                onClick={() =>
                  setFilter(
                    item
                  )
                }
                style={{
                  border:
                    filter ===
                    item
                      ? "1px solid #0f172a"
                      : "1px solid transparent",
                  borderRadius:
                    "7px",
                  padding:
                    "8px 11px",
                  background:
                    filter ===
                    item
                      ? "#0f172a"
                      : "#ffffff",
                  color:
                    filter ===
                    item
                      ? "#ffffff"
                      : "#64748b",
                  fontSize:
                    "9px",
                  fontWeight:
                    800,
                  letterSpacing:
                    "0.06em",
                  cursor:
                    "pointer",
                }}
              >
                {item}
              </button>
            )
          )}
        </div>

        <select
          value={
            priorityFilter
          }
          onChange={(event) =>
            setPriorityFilter(
              event.target.value
            )
          }
          style={{
            border:
              "1px solid #dbe3ec",
            borderRadius:
              "8px",
            padding:
              "9px 10px",
            background:
              "#ffffff",
            color:
              "#334155",
            fontSize:
              "10px",
            fontWeight:
              700,
          }}
        >
          <option value="ALL">
            ALL PRIORITIES
          </option>

          <option value="HIGH">
            HIGH PRIORITY
          </option>

          <option value="MEDIUM">
            MEDIUM PRIORITY
          </option>

          <option value="LOW">
            LOW PRIORITY
          </option>
        </select>

        <select
          value={
            typeFilter
          }
          onChange={(event) =>
            setTypeFilter(
              event.target.value
            )
          }
          style={{
            border:
              "1px solid #dbe3ec",
            borderRadius:
              "8px",
            padding:
              "9px 10px",
            background:
              "#ffffff",
            color:
              "#334155",
            fontSize:
              "10px",
            fontWeight:
              700,
          }}
        >
          <option value="ALL">
            ALL CHANGE TYPES
          </option>

          <option value="CONSTRUCTION">
            CONSTRUCTION
          </option>

          <option value="ROAD DEVELOPMENT">
            ROAD DEVELOPMENT
          </option>

          <option value="CLEARANCE / ACTIVITY">
            CLEARANCE / ACTIVITY
          </option>

          <option value="OTHER CHANGE">
            OTHER CHANGE
          </option>
        </select>
      </div>

      {visibleEvents.length ===
      0 ? (
        <div
          style={{
            border:
              "1px solid #e2e8f0",
            borderRadius:
              "12px",
            background:
              "#ffffff",
            padding:
              "55px 25px",
            textAlign:
              "center",
          }}
        >
          <div
            style={{
              fontSize:
                "11px",
              fontWeight:
                800,
              letterSpacing:
                "0.1em",
              color:
                "#64748b",
            }}
          >
            NO EVENTS MATCH THIS QUEUE
          </div>

          <p
            style={{
              margin:
                "8px 0 0",
              color:
                "#94a3b8",
              fontSize:
                "12px",
            }}
          >
            Try another review status, priority or change-type filter.
          </p>
        </div>
      ) : (
        <div
          style={{
            display:
              "flex",
            flexDirection:
              "column",
            gap:
              "12px",
          }}
        >
          {visibleEvents.map(
            (event) => {
              const tile =
                Number(
                  event?.tile_id
                );

              const existingReview =
                reviews[tile];

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

              const jewar =
                isJewarEvent(
                  event
                );

              return (
                <article
                  key={
                    tile
                  }
                  style={{
                    border:
                      "1px solid #dfe5ec",
                    borderRadius:
                      "12px",
                    background:
                      "#ffffff",
                    overflow:
                      "hidden",
                  }}
                >
                  <div
                    style={{
                      display:
                        "grid",
                      gridTemplateColumns:
                        "180px 180px minmax(0, 1fr) 150px",
                      gap:
                        "0",
                    }}
                  >
                    <div
                      style={{
                        height:
                          "150px",
                        background:
                          "#f1f5f9",
                      }}
                    >
                      <img
                        src={`${API_BASE_URL}/change-events/${tile}/evidence/before?v=5`}
                        alt={`Before evidence for tile ${tile}`}
                        style={{
                          display:
                            "block",
                          width:
                            "100%",
                          height:
                            "150px",
                          objectFit:
                            "cover",
                        }}
                      />
                    </div>

                    <div
                      style={{
                        height:
                          "150px",
                        background:
                          "#f1f5f9",
                      }}
                    >
                      <img
                        src={`${API_BASE_URL}/change-events/${tile}/evidence/after?v=5`}
                        alt={`After evidence for tile ${tile}`}
                        style={{
                          display:
                            "block",
                          width:
                            "100%",
                          height:
                            "150px",
                          objectFit:
                            "cover",
                        }}
                      />
                    </div>

                    <div
                      style={{
                        padding:
                          "18px 20px",
                        minWidth:
                          0,
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
                          flexWrap:
                            "wrap",
                        }}
                      >
                        <QueueStatusBadge
                          label={`TILE ${tile}`}
                        />

                        <QueueStatusBadge
                          label={
                            priority
                          }
                          tone={
                            priority ===
                            "HIGH"
                              ? "red"
                              : priority ===
                                "MEDIUM"
                              ? "amber"
                              : "neutral"
                          }
                        />

                        <QueueStatusBadge
                          label={
                            confidence
                          }
                        />

                        {jewar && (
                          <QueueStatusBadge
                            label="JEWAR"
                            tone="green"
                          />
                        )}

                        {existingReview && (
                          <QueueStatusBadge
                            label={
                              existingReview.decision
                            }
                            tone={
                              existingReview.decision ===
                              "CONFIRMED"
                                ? "green"
                                : "red"
                            }
                          />
                        )}
                      </div>

                      <h3
                        style={{
                          margin:
                            "12px 0 6px",
                          fontSize:
                            "17px",
                          color:
                            "#0f172a",
                        }}
                      >
                        {
                          changeType
                        }
                      </h3>

                      <div
                        style={{
                          fontSize:
                            "10px",
                          color:
                            "#64748b",
                          marginBottom:
                            "12px",
                          fontWeight:
                            700,
                        }}
                      >
                        {getLocationLabel(
                          event
                        )}
                      </div>

                      <div
                        style={{
                          display:
                            "grid",
                          gridTemplateColumns:
                            "repeat(4, minmax(0, 1fr))",
                          gap:
                            "12px",
                        }}
                      >
                        <InfoItem
                          label="CHANGE"
                          value={formatPercentage(
                            event?.change_percentage
                          )}
                        />

                        <InfoItem
                          label="EVIDENCE"
                          value={formatScore(
                            event?.evidence_score
                          )}
                        />

                        <InfoItem
                          label="SEVERITY"
                          value={formatScore(
                            event?.severity_score
                          )}
                        />

                        <InfoItem
                          label="RISK"
                          value={
                            event?.false_alarm_risk ??
                            "LOW"
                          }
                        />
                      </div>
                    </div>

                    <div
                      style={{
                        padding:
                          "18px",
                        display:
                          "flex",
                        alignItems:
                          "center",
                        justifyContent:
                          "center",
                        borderLeft:
                          "1px solid #eef2f6",
                      }}
                    >
                      <button
                        type="button"
                        onClick={() =>
                          navigate(
                            `/review/${tile}`
                          )
                        }
                        style={{
                          width:
                            "100%",
                          border:
                            "1px solid #0f172a",
                          borderRadius:
                            "8px",
                          padding:
                            "11px 12px",
                          background:
                            "#0f172a",
                          color:
                            "#ffffff",
                          fontSize:
                            "10px",
                          fontWeight:
                            800,
                          letterSpacing:
                            "0.07em",
                          cursor:
                            "pointer",
                        }}
                      >
                        {existingReview
                          ? "OPEN REVIEW"
                          : "REVIEW EVENT"}
                      </button>
                    </div>
                  </div>

                  <div
                    style={{
                      display:
                        "grid",
                      gridTemplateColumns:
                        "1fr 1fr",
                      borderTop:
                        "1px solid #eef2f6",
                      background:
                        "#fafbfc",
                    }}
                  >
                    <div
                      style={{
                        padding:
                          "8px 12px",
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
                      BEFORE EVIDENCE
                    </div>

                    <div
                      style={{
                        padding:
                          "8px 12px",
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
                      AFTER EVIDENCE
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

/* ============================================================
   SINGLE EVENT REVIEW
============================================================ */

export default function ReviewPage() {
  /*
   * IMPORTANT:
   * ALL HOOKS MUST RUN BEFORE ANY CONDITIONAL RETURN.
   *
   * This fixes the React hook-order crash that occurred when
   * switching between /review and /review/:tileId.
   */

  const {
    tileId,
  } = useParams();

  const navigate =
    useNavigate();

  const numericTileId =
    Number(tileId);

  const [event, setEvent] =
    useState(null);

  const [review, setReview] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [note, setNote] =
    useState("");

  const [submitting, setSubmitting] =
    useState(false);

  const [submitError, setSubmitError] =
    useState("");

  const [successMessage, setSuccessMessage] =
    useState("");

  /* ============================================================
     LOAD REVIEW DATA
  ============================================================ */

  useEffect(() => {
    /*
     * Queue page does not need single-event API calls.
     */

    if (
      tileId ===
      undefined
    ) {
      setLoading(false);
      return;
    }

    let cancelled =
      false;

    async function loadReviewData() {
      try {
        setLoading(true);
        setError("");

        const [
          eventResponse,
          reviewResponse,
        ] =
          await Promise.all([
            fetch(
              `${API_BASE_URL}/change-events/${numericTileId}`
            ),

            fetch(
              `${API_BASE_URL}/change-events/${numericTileId}/review`
            ),
          ]);

        if (
          !eventResponse.ok
        ) {
          throw new Error(
            `Change event HTTP ${eventResponse.status}`
          );
        }

        const eventData =
          await eventResponse.json();

        let reviewData =
          null;

        if (
          reviewResponse.ok
        ) {
          reviewData =
            await reviewResponse.json();
        }

        if (cancelled) {
          return;
        }

        setEvent(
          eventData
        );

        if (
          reviewData?.reviewed &&
          reviewData?.review
        ) {
          setReview(
            reviewData.review
          );

          setNote(
            reviewData.review.note ??
              ""
          );
        } else {
          setReview(null);
          setNote("");
        }
      } catch (
        requestError
      ) {
        console.error(
          "ORION review data failed:",
          requestError
        );

        if (
          !cancelled
        ) {
          setError(
            "Review data could not be loaded. Check the ORION backend."
          );
        }
      } finally {
        if (
          !cancelled
        ) {
          setLoading(false);
        }
      }
    }

    if (
      Number.isFinite(
        numericTileId
      )
    ) {
      loadReviewData();
    } else {
      setError(
        "Invalid change event ID."
      );

      setLoading(false);
    }

    return () => {
      cancelled = true;
    };
  }, [
    tileId,
    numericTileId,
  ]);

  /* ============================================================
     QUEUE ROUTE
  ============================================================ */

  if (
    tileId ===
    undefined
  ) {
    return (
      <ReviewQueuePage />
    );
  }

  /* ============================================================
     EVIDENCE URLS
  ============================================================ */

  const beforeUrl =
    `${API_BASE_URL}/change-events/${numericTileId}/evidence/before?v=7`;

  const afterUrl =
    `${API_BASE_URL}/change-events/${numericTileId}/evidence/after?v=7`;

  const maskUrl =
    `${API_BASE_URL}/change-events/${numericTileId}/evidence/mask?v=7`;

  /* ============================================================
     SUBMIT REVIEW
  ============================================================ */

  async function submitReview(
    decision
  ) {
    const normalizedDecision =
      String(
        decision
      ).toUpperCase();

    if (
      normalizedDecision !==
        "CONFIRMED" &&
      normalizedDecision !==
        "REJECTED"
    ) {
      return;
    }

    try {
      setSubmitting(
        true
      );

      setSubmitError(
        ""
      );

      setSuccessMessage(
        ""
      );

      const response =
        await fetch(
          `${API_BASE_URL}/change-events/${numericTileId}/review`,
          {
            method:
              "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                decision:
                  normalizedDecision,

                note:
                  note.trim(),
              }),
          }
        );

      let data =
        null;

      try {
        data =
          await response.json();
      } catch {
        data =
          null;
      }

      if (
        !response.ok
      ) {
        throw new Error(
          data?.detail ??
            `HTTP ${response.status}`
        );
      }

      const savedReview =
        data?.review ??
        null;

      setReview(
        savedReview
      );

      if (
        savedReview?.note !==
        undefined
      ) {
        setNote(
          savedReview.note
        );
      }

      setSuccessMessage(
        `Event ${numericTileId} marked ${normalizedDecision}.`
      );
    } catch (
      requestError
    ) {
      console.error(
        "ORION review submission failed:",
        requestError
      );

      setSubmitError(
        requestError.message ||
          "Review could not be saved."
      );
    } finally {
      setSubmitting(
        false
      );
    }
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
            "1450px",
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
            LOADING ANALYST REVIEW
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
            Retrieving change evidence and review history...
          </div>
        </div>
      </section>
    );
  }

  /* ============================================================
     ERROR
  ============================================================ */

  if (
    error ||
    !event
  ) {
    return (
      <section
        style={{
          padding:
            "40px 24px",
          maxWidth:
            "1450px",
          margin:
            "0 auto",
        }}
      >
        <div
          style={{
            border:
              "1px solid #fecaca",
            borderRadius:
              "14px",
            background:
              "#fff7f7",
            padding:
              "40px",
          }}
        >
          <div
            style={{
              fontSize:
                "13px",
              fontWeight:
                800,
              color:
                "#991b1b",
            }}
          >
            REVIEW DATA UNAVAILABLE
          </div>

          <div
            style={{
              marginTop:
                "8px",
              color:
                "#7f1d1d",
              fontSize:
                "12px",
            }}
          >
            {error}
          </div>

          <button
            type="button"
            onClick={() =>
              navigate(
                "/changes"
              )
            }
            style={{
              marginTop:
                "20px",
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
              cursor:
                "pointer",
            }}
          >
            ← BACK TO CHANGES
          </button>
        </div>
      </section>
    );
  }

  /* ============================================================
     EVENT METADATA
  ============================================================ */

  const jewar =
    isJewarEvent(
      event
    );

  const datasetLabel =
    getDatasetLabel(
      event
    );

  const locationLabel =
    getLocationLabel(
      event
    );

  const sensorLabel =
    getSensorLabel(
      event
    );

  const productLabel =
    getProductLabel(
      event
    );

  const resolutionLabel =
    getResolutionLabel(
      event
    );

  const mgrsLabel =
    getMGRSLabel(
      event
    );

  const crsLabel =
    getCRSLabel(
      event
    );

  const pixelSizeLabel =
    getPixelSizeLabel(
      event
    );

  const beforeDate =
    event?.before_date ??
    event?.before?.date ??
    "—";

  const afterDate =
    event?.after_date ??
    event?.after?.date ??
    "—";

  const changePercentage =
    Number(
      event?.change_percentage ??
        0
    );

  const severity =
    Number(
      event?.severity_score ??
        0
    );

  const evidenceScore =
    Number(
      event?.evidence_score ??
        0
    );

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

  const falseAlarmRisk =
    String(
      event?.false_alarm_risk ??
        "LOW"
    ).toUpperCase();

  const changeType =
    event?.dominant_change_type ??
    "OTHER CHANGE";

  /* ============================================================
     RENDER
  ============================================================ */

  return (
    <section
      style={{
        padding:
          "30px 24px 55px",
        maxWidth:
          "1450px",
        margin:
          "0 auto",
      }}
    >

      {/* ======================================================
          HEADER
      ====================================================== */}

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
            "22px",
        }}
      >
        <div>

          <div
            style={{
              fontSize:
                "11px",
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
            ANALYST REVIEW
          </div>

          <h2
            style={{
              margin:
                0,
              fontSize:
                "30px",
              letterSpacing:
                "-0.03em",
              color:
                "#0f172a",
            }}
          >
            {jewar
              ? `Jewar Event · Tile ${numericTileId}`
              : `Change Event · Tile ${numericTileId}`}
          </h2>

          <p
            style={{
              margin:
                "8px 0 0",
              color:
                "#64748b",
              fontSize:
                "14px",
              lineHeight:
                1.6,
            }}
          >
            Review the temporal evidence, assess the automated analysis, and record an analyst decision.
          </p>

          <div
            style={{
              marginTop:
                "10px",
              display:
                "flex",
              flexWrap:
                "wrap",
              gap:
                "7px",
            }}
          >
            <QueueStatusBadge
              label={
                datasetLabel
              }
              tone={
                jewar
                  ? "green"
                  : "neutral"
              }
            />

            <QueueStatusBadge
              label={
                locationLabel
              }
            />
          </div>

        </div>

        <button
          type="button"
          onClick={() =>
            navigate(
              "/changes"
            )
          }
          style={{
            border:
              "1px solid #cbd5e1",
            borderRadius:
              "8px",
            padding:
              "10px 14px",
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
          ← BACK TO CHANGES
        </button>
      </div>

      {/* ======================================================
          DATASET CONTEXT
      ====================================================== */}

      <div
        style={{
          border:
            "1px solid #e2e8f0",
          borderRadius:
            "12px",
          background:
            "#ffffff",
          padding:
            "18px",
          marginBottom:
            "18px",
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
              "14px",
          }}
        >
          DATASET CONTEXT
        </div>

        <div
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(4, minmax(0, 1fr))",
            gap:
              "18px",
          }}
        >

          <InfoItem
            label="DATASET"
            value={
              datasetLabel
            }
          />

          <InfoItem
            label="LOCATION"
            value={
              locationLabel
            }
          />

          <InfoItem
            label="SENSOR"
            value={
              sensorLabel
            }
          />

          <InfoItem
            label="PRODUCT"
            value={
              productLabel
            }
          />

          <InfoItem
            label="SPATIAL RESOLUTION"
            value={
              resolutionLabel
            }
          />

          <InfoItem
            label="PIXEL SIZE"
            value={
              pixelSizeLabel
            }
          />

          <InfoItem
            label="SOURCE CRS"
            value={
              crsLabel
            }
          />

          <InfoItem
            label="MGRS TILE"
            value={
              mgrsLabel
            }
          />

        </div>

      </div>

      {/* ======================================================
          CURRENT REVIEW
      ====================================================== */}

      {review && (
        <div
          style={{
            marginBottom:
              "18px",
            padding:
              "14px 16px",
            border:
              "1px solid #dbe3ec",
            borderRadius:
              "10px",
            background:
              "#ffffff",
            display:
              "flex",
            justifyContent:
              "space-between",
            alignItems:
              "center",
            gap:
              "16px",
          }}
        >
          <div>

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
              }}
            >
              EXISTING ANALYST DECISION
            </div>

            <div
              style={{
                marginTop:
                  "6px",
                fontSize:
                  "12px",
                color:
                  "#475569",
              }}
            >
              {review.reviewed_at
                ? `Reviewed at ${review.reviewed_at}`
                : "Previously reviewed"}
            </div>

          </div>

          <DecisionBadge
            decision={
              review.decision
            }
          />
        </div>
      )}

      {/* ======================================================
          TEMPORAL EVIDENCE
      ====================================================== */}

      <div
        style={{
          display:
            "grid",
          gridTemplateColumns:
            "1fr 1fr",
          gap:
            "16px",
          marginBottom:
            "18px",
        }}
      >

        <EvidencePanel
          label={`BEFORE · ${formatDate(
            beforeDate
          )}`}
          src={
            beforeUrl
          }
        />

        <EvidencePanel
          label={`AFTER · ${formatDate(
            afterDate
          )}`}
          src={
            afterUrl
          }
        />

      </div>

      {/* ======================================================
          MASK
      ====================================================== */}

      <div
        style={{
          border:
            "1px solid #e2e8f0",
          borderRadius:
            "12px",
          background:
            "#ffffff",
          padding:
            "16px",
          marginBottom:
            "18px",
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
              "10px",
          }}
        >
          DETECTED CHANGE MASK
        </div>

        <div
          style={{
            width:
              "100%",
            maxWidth:
              "520px",
            borderRadius:
              "8px",
            overflow:
              "hidden",
            background:
              "#0f172a",
          }}
        >
          <img
            src={
              maskUrl
            }
            alt="Detected change mask"
            style={{
              display:
                "block",
              width:
                "100%",
              height:
                "auto",
            }}
          />
        </div>

        <div
          style={{
            marginTop:
              "10px",
            fontSize:
              "10px",
            color:
              "#64748b",
            lineHeight:
              1.5,
          }}
        >
          The mask represents the spatial regions identified by ORION's temporal change detector.
        </div>

      </div>

      {/* ======================================================
          AUTOMATED ANALYSIS
      ====================================================== */}

      <div
        style={{
          border:
            "1px solid #e2e8f0",
          borderRadius:
            "12px",
          background:
            "#ffffff",
          padding:
            "18px",
          marginBottom:
            "18px",
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
              "13px",
          }}
        >
          AUTOMATED ANALYSIS
        </div>

        <div
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(5, minmax(0, 1fr))",
            gap:
              "10px",
            marginBottom:
              "18px",
          }}
        >

          <MetricCard
            label="CHANGE"
            value={
              formatPercentage(
                changePercentage
              )
            }
          />

          <MetricCard
            label="SEVERITY"
            value={
              formatScore(
                severity
              )
            }
          />

          <MetricCard
            label="EVIDENCE"
            value={
              formatScore(
                evidenceScore
              )
            }
          />

          <MetricCard
            label="PRIORITY"
            value={
              <StatusBadge
                label={
                  priority
                }
              />
            }
          />

          <MetricCard
            label="CONFIDENCE"
            value={
              <StatusBadge
                label={
                  confidence
                }
              />
            }
          />

        </div>

        <div
          style={{
            display:
              "grid",
            gridTemplateColumns:
              "repeat(4, minmax(0, 1fr))",
            gap:
              "18px",
          }}
        >

          <InfoItem
            label="CHANGE TYPE"
            value={
              changeType
            }
          />

          <InfoItem
            label="FALSE-ALARM RISK"
            value={
              falseAlarmRisk
            }
          />

          <InfoItem
            label="CHANGED PIXELS"
            value={
              event?.changed_pixels ??
              0
            }
          />

          <InfoItem
            label="CHANGE REGIONS"
            value={
              event?.change_regions ??
              0
            }
          />

          <InfoItem
            label="PIXEL X / CENTROID X"
            value={
              event?.x ??
              "—"
            }
          />

          <InfoItem
            label="PIXEL Y / CENTROID Y"
            value={
              event?.y ??
              "—"
            }
          />

          <InfoItem
            label="CLASSIFICATION SCORE"
            value={
              formatScore(
                event?.classification_score
              )
            }
          />

          <InfoItem
            label="MEAN CHANGE INTENSITY"
            value={
              formatScore(
                event?.mean_change_intensity
              )
            }
          />

        </div>

      </div>

      {/* ======================================================
          EVIDENCE SIGNALS
      ====================================================== */}

      {Array.isArray(
        event?.evidence
      ) &&
        event.evidence.length >
          0 && (
          <div
            style={{
              border:
                "1px solid #e2e8f0",
              borderRadius:
                "12px",
              background:
                "#ffffff",
              padding:
                "18px",
              marginBottom:
                "18px",
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
                  "10px",
              }}
            >
              EVIDENCE SIGNALS
            </div>

            <div
              style={{
                display:
                  "flex",
                flexDirection:
                  "column",
                gap:
                  "7px",
              }}
            >

              {event.evidence.map(
                (
                  item,
                  index
                ) => (
                  <div
                    key={
                      `${numericTileId}-evidence-${index}`
                    }
                    style={{
                      fontSize:
                        "12px",
                      color:
                        "#475569",
                      padding:
                        "7px 9px",
                      border:
                        "1px solid #eef2f6",
                      borderRadius:
                        "6px",
                      background:
                        "#fafbfc",
                      wordBreak:
                        "break-word",
                    }}
                  >
                    •{" "}
                    {evidenceText(
                      item
                    )}
                  </div>
                )
              )}

            </div>
          </div>
        )}

      {/* ======================================================
          FALSE ALARM REASONS
      ====================================================== */}

      {Array.isArray(
        event?.false_alarm_reasons
      ) &&
        event
          .false_alarm_reasons
          .length >
          0 && (
          <div
            style={{
              border:
                "1px solid #e2e8f0",
              borderRadius:
                "12px",
              background:
                "#ffffff",
              padding:
                "18px",
              marginBottom:
                "18px",
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
                  "10px",
              }}
            >
              FALSE-ALARM CONSIDERATIONS
            </div>

            {event.false_alarm_reasons.map(
              (
                reason,
                index
              ) => (
                <div
                  key={
                    `reason-${index}`
                  }
                  style={{
                    fontSize:
                      "11px",
                    color:
                      "#475569",
                    marginBottom:
                      "5px",
                    lineHeight:
                      1.5,
                  }}
                >
                  •{" "}
                  {safeText(
                    reason
                  )}
                </div>
              )
            )}

          </div>
        )}

      {/* ======================================================
          ANALYST DECISION
      ====================================================== */}

      <div
        style={{
          border:
            "1px solid #cbd5e1",
          borderRadius:
            "12px",
          background:
            "#ffffff",
          padding:
            "20px",
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
              "8px",
          }}
        >
          ANALYST DECISION
        </div>

        <div
          style={{
            fontSize:
              "13px",
            color:
              "#475569",
            lineHeight:
              1.6,
            marginBottom:
              "14px",
          }}
        >
          Confirm the detected change if
          the temporal evidence supports
          it. Reject it when the evidence
          indicates a false alarm or
          insufficient change.
        </div>

        <label
          style={{
            display:
              "block",
          }}
        >

          <div
            style={{
              fontSize:
                "9px",
              fontWeight:
                800,
              letterSpacing:
                "0.09em",
              color:
                "#64748b",
              marginBottom:
                "7px",
            }}
          >
            ANALYST NOTE
          </div>

          <textarea
            value={
              note
            }
            onChange={(
              event
            ) =>
              setNote(
                event.target.value
              )
            }
            placeholder="Enter the reasoning behind the analyst decision..."
            rows={
              5
            }
            style={{
              width:
                "100%",
              boxSizing:
                "border-box",
              resize:
                "vertical",
              border:
                "1px solid #dbe3ec",
              borderRadius:
                "8px",
              padding:
                "11px",
              background:
                "#ffffff",
              color:
                "#0f172a",
              fontFamily:
                "inherit",
              fontSize:
                "12px",
              lineHeight:
                1.5,
              outline:
                "none",
            }}
          />

        </label>

        {submitError && (
          <div
            style={{
              marginTop:
                "12px",
              padding:
                "11px 12px",
              border:
                "1px solid #fecaca",
              borderRadius:
                "8px",
              background:
                "#fff7f7",
              color:
                "#991b1b",
              fontSize:
                "12px",
            }}
          >
            {submitError}
          </div>
        )}

        {successMessage && (
          <div
            style={{
              marginTop:
                "12px",
              padding:
                "11px 12px",
              border:
                "1px solid #bbf7d0",
              borderRadius:
                "8px",
              background:
                "#f0fdf4",
              color:
                "#166534",
              fontSize:
                "12px",
              fontWeight:
                700,
            }}
          >
            {successMessage}
          </div>
        )}

        <div
          style={{
            display:
              "flex",
            justifyContent:
              "flex-end",
            gap:
              "10px",
            marginTop:
              "16px",
          }}
        >

          <button
            type="button"
            disabled={
              submitting
            }
            onClick={() =>
              submitReview(
                "REJECTED"
              )
            }
            style={{
              border:
                "1px solid #fecaca",
              borderRadius:
                "8px",
              padding:
                "10px 16px",
              background:
                "#ffffff",
              color:
                "#991b1b",
              fontSize:
                "10px",
              fontWeight:
                800,
              letterSpacing:
                "0.06em",
              cursor:
                submitting
                  ? "not-allowed"
                  : "pointer",
              opacity:
                submitting
                  ? 0.6
                  : 1,
            }}
          >
            {submitting
              ? "SAVING..."
              : "REJECT CHANGE"}
          </button>

          <button
            type="button"
            disabled={
              submitting
            }
            onClick={() =>
              submitReview(
                "CONFIRMED"
              )
            }
            style={{
              border:
                "1px solid #bbf7d0",
              borderRadius:
                "8px",
              padding:
                "10px 16px",
              background:
                "#f0fdf4",
              color:
                "#166534",
              fontSize:
                "10px",
              fontWeight:
                800,
              letterSpacing:
                "0.06em",
              cursor:
                submitting
                  ? "not-allowed"
                  : "pointer",
              opacity:
                submitting
                  ? 0.6
                  : 1,
            }}
          >
            {submitting
              ? "SAVING..."
              : "CONFIRM CHANGE"}
          </button>

        </div>

        <div
          style={{
            marginTop:
              "12px",
            fontSize:
              "10px",
            color:
              "#94a3b8",
            lineHeight:
              1.5,
          }}
        >
          Analyst decisions are recorded
          through the ORION review API and
          retained in the review audit history.
        </div>

      </div>

    </section>
  );
}