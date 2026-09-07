import { useState } from "react";

const API_BASE_URL =
  "http://127.0.0.1:8000";

export default function IngestionPage() {
  const [inputPath, setInputPath] = useState(
    "data/tiles/prayagraj/before"
  );

  const [sceneId, setSceneId] = useState(
    "prayagraj"
  );

  const [observation, setObservation] = useState(
    "before"
  );

  const [indexDir, setIndexDir] = useState(
    "data/indexes/incremental_real_test"
  );

  const [reloadSearch, setReloadSearch] =
    useState(true);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [result, setResult] =
    useState(null);

  async function handleIngest() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/ingest/incremental`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            input_path:
              inputPath.trim(),

            scene_id:
              sceneId.trim(),

            observation,

            index_dir:
              indexDir.trim(),

            model_path: null,

            reload_search:
              reloadSearch,
          }),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            `HTTP ${response.status}`
        );
      }

      setResult(data);

    } catch (requestError) {
      console.error(
        "ORION incremental ingestion failed:",
        requestError
      );

      setError(
        requestError.message ||
          "Incremental ingestion failed."
      );
    } finally {
      setLoading(false);
    }
  }

  const ingestion =
    result?.ingestion;

  return (
    <section className="orion-page">
      <div
        style={{
          maxWidth: "1100px",
          margin: "0 auto",
          padding: "32px 24px 60px",
        }}
      >
        {/* HEADER */}

        <div
          style={{
            marginBottom: "28px",
          }}
        >
          <div
            style={{
              fontSize: "12px",
              fontWeight: 700,
              letterSpacing: "0.14em",
              marginBottom: "8px",
            }}
          >
            ORION / DATA PIPELINE
          </div>

          <h2
            style={{
              margin: 0,
              fontSize: "32px",
              letterSpacing: "-0.02em",
            }}
          >
            Incremental Ingestion
          </h2>

          <p
            style={{
              marginTop: "10px",
              maxWidth: "760px",
              lineHeight: 1.6,
              color: "#5f6368",
            }}
          >
            Add new satellite tiles to an
            existing RemoteCLIP + FAISS
            semantic-search index without
            rebuilding the complete index.
          </p>
        </div>

        {/* FORM */}

        <div
          style={{
            border: "1px solid #dfe3e8",
            borderRadius: "12px",
            padding: "24px",
            background: "#ffffff",
            boxShadow:
              "0 4px 18px rgba(0, 0, 0, 0.05)",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "20px",
            }}
          >
            {/* INPUT PATH */}

            <label
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                }}
              >
                TILE INPUT DIRECTORY
              </span>

              <input
                value={inputPath}
                onChange={(event) =>
                  setInputPath(
                    event.target.value
                  )
                }
                placeholder="data/tiles/prayagraj/before"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "12px 14px",
                  border:
                    "1px solid #cfd4da",
                  borderRadius: "7px",
                  fontSize: "14px",
                  background: "#fff",
                }}
              />
            </label>

            {/* SCENE ID */}

            <label
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                }}
              >
                SCENE ID
              </span>

              <input
                value={sceneId}
                onChange={(event) =>
                  setSceneId(
                    event.target.value
                  )
                }
                placeholder="prayagraj"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "12px 14px",
                  border:
                    "1px solid #cfd4da",
                  borderRadius: "7px",
                  fontSize: "14px",
                  background: "#fff",
                }}
              />
            </label>

            {/* OBSERVATION */}

            <label
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                }}
              >
                OBSERVATION
              </span>

              <select
                value={observation}
                onChange={(event) =>
                  setObservation(
                    event.target.value
                  )
                }
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "12px 14px",
                  border:
                    "1px solid #cfd4da",
                  borderRadius: "7px",
                  fontSize: "14px",
                  background: "#fff",
                }}
              >
                <option value="before">
                  BEFORE
                </option>

                <option value="after">
                  AFTER
                </option>
              </select>
            </label>

            {/* INDEX DIRECTORY */}

            <label
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                }}
              >
                FAISS INDEX DIRECTORY
              </span>

              <input
                value={indexDir}
                onChange={(event) =>
                  setIndexDir(
                    event.target.value
                  )
                }
                placeholder="data/indexes/incremental_real_test"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "12px 14px",
                  border:
                    "1px solid #cfd4da",
                  borderRadius: "7px",
                  fontSize: "14px",
                  background: "#fff",
                }}
              />
            </label>
          </div>

          {/* RELOAD OPTION */}

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginTop: "22px",
              fontSize: "14px",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={reloadSearch}
              onChange={(event) =>
                setReloadSearch(
                  event.target.checked
                )
              }
            />

            Reload semantic search after
            ingestion
          </label>

          {/* WARNING */}

          <div
            style={{
              marginTop: "20px",
              padding: "14px 16px",
              borderRadius: "8px",
              background: "#f7f8fa",
              border:
                "1px solid #e2e5e9",
              fontSize: "13px",
              lineHeight: 1.6,
              color: "#555",
            }}
          >
            Current default target is the
            safe incremental test index:
            <strong>
              {" "}
              data/indexes/incremental_real_test
            </strong>
            .
            <br />
            This prevents accidental
            modification of the production
            Prayagraj index during testing.
          </div>

          {/* BUTTON */}

          <button
            type="button"
            onClick={handleIngest}
            disabled={
              loading ||
              !inputPath.trim() ||
              !sceneId.trim() ||
              !indexDir.trim()
            }
            style={{
              marginTop: "22px",
              padding: "13px 22px",
              border: "none",
              borderRadius: "7px",
              background:
                loading
                  ? "#9aa0a6"
                  : "#111827",
              color: "#ffffff",
              fontSize: "13px",
              fontWeight: 700,
              letterSpacing: "0.06em",
              cursor:
                loading
                  ? "wait"
                  : "pointer",
            }}
          >
            {loading
              ? "INGESTING..."
              : "START INCREMENTAL INGESTION"}
          </button>
        </div>

        {/* ERROR */}

        {error && (
          <div
            style={{
              marginTop: "20px",
              padding: "16px",
              borderRadius: "8px",
              border:
                "1px solid #e2b8b8",
              background: "#fff6f6",
              color: "#9b1c1c",
              lineHeight: 1.5,
            }}
          >
            <strong>
              INGESTION FAILED
            </strong>

            <div
              style={{
                marginTop: "6px",
              }}
            >
              {error}
            </div>
          </div>
        )}

        {/* SUCCESS */}

        {result && ingestion && (
          <div
            style={{
              marginTop: "24px",
              border:
                "1px solid #dfe3e8",
              borderRadius: "12px",
              padding: "24px",
              background: "#ffffff",
              boxShadow:
                "0 4px 18px rgba(0, 0, 0, 0.04)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent:
                  "space-between",
                gap: "20px",
                flexWrap: "wrap",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 700,
                    letterSpacing:
                      "0.12em",
                    marginBottom: "7px",
                  }}
                >
                  INGESTION COMPLETE
                </div>

                <h3
                  style={{
                    margin: 0,
                    fontSize: "24px",
                  }}
                >
                  Index updated successfully
                </h3>
              </div>

              <div
                style={{
                  padding: "8px 12px",
                  borderRadius: "20px",
                  background: "#eef8f0",
                  color: "#236b35",
                  fontSize: "12px",
                  fontWeight: 700,
                }}
              >
                SUCCESS
              </div>
            </div>

            {/* METRICS */}

            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(150px, 1fr))",
                gap: "12px",
                marginTop: "24px",
              }}
            >
              <Metric
                label="IMAGES DISCOVERED"
                value={
                  ingestion.images_discovered ??
                  "—"
                }
              />

              <Metric
                label="IMAGES SKIPPED"
                value={
                  ingestion.images_skipped ??
                  "—"
                }
              />

              <Metric
                label="IMAGES ADDED"
                value={
                  ingestion.images_added ??
                  "—"
                }
              />

              <Metric
                label="VECTORS BEFORE"
                value={
                  ingestion.vectors_before ??
                  "—"
                }
              />

              <Metric
                label="VECTORS ADDED"
                value={
                  ingestion.vectors_added ??
                  "—"
                }
              />

              <Metric
                label="VECTORS AFTER"
                value={
                  ingestion.vectors_after ??
                  "—"
                }
              />
            </div>

            {/* SEARCH RELOAD */}

            <div
              style={{
                marginTop: "20px",
                padding: "14px 16px",
                borderRadius: "8px",
                background:
                  result.semantic_search_reloaded
                    ? "#f1f8f3"
                    : "#f7f8fa",
                border:
                  "1px solid #e0e5e2",
                fontSize: "13px",
              }}
            >
              Semantic search reloaded:

              <strong>
                {" "}
                {result.semantic_search_reloaded
                  ? "YES"
                  : "NO"}
              </strong>

              <br />

              Active index:

              <strong>
                {" "}
                {result.active_index_dir ||
                  "—"}
              </strong>
            </div>

            {/* TECHNICAL STATUS */}

            <details
              style={{
                marginTop: "18px",
              }}
            >
              <summary
                style={{
                  cursor: "pointer",
                  fontSize: "13px",
                  fontWeight: 700,
                }}
              >
                View technical ingestion
                details
              </summary>

              <pre
                style={{
                  marginTop: "12px",
                  padding: "16px",
                  overflowX: "auto",
                  borderRadius: "8px",
                  background: "#f5f6f7",
                  fontSize: "12px",
                  lineHeight: 1.5,
                }}
              >
                {JSON.stringify(
                  result,
                  null,
                  2
                )}
              </pre>
            </details>
          </div>
        )}
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
}) {
  return (
    <div
      style={{
        padding: "16px",
        border:
          "1px solid #e1e4e8",
        borderRadius: "8px",
        background: "#fafbfc",
      }}
    >
      <div
        style={{
          fontSize: "10px",
          fontWeight: 700,
          letterSpacing: "0.08em",
          color: "#6b7280",
        }}
      >
        {label}
      </div>

      <div
        style={{
          marginTop: "8px",
          fontSize: "24px",
          fontWeight: 700,
        }}
      >
        {value}
      </div>
    </div>
  );
}