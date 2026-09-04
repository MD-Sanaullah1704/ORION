import { useState } from "react";
import SceneDetail from "./components/SceneDetail";
import demoScenes from "./data/demoScenes";

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [selectedScene, setSelectedScene] = useState(null);

  function handleSearch() {
    const trimmedQuery = query.trim();

    if (!trimmedQuery) {
      setResults([]);
      setSearched(false);
      return;
    }

    setResults(demoScenes);
    setSearched(true);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter") {
      handleSearch();
    }
  }

  return (
    <div className="app">

      {/* HEADER */}
      <header className="top-header">
        <div>
          <h1>ORION</h1>
          <p>OFFLINE SATELLITE INTELLIGENCE</p>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          SYSTEM READY
        </div>
      </header>

      {/* SEARCH */}
      <main>

        <section className="hero">
          <span className="section-label">
            01 / INTELLIGENCE QUERY
          </span>

          <h2>
            FIND
            <br />
            <span>WHAT CHANGED.</span>
          </h2>

          <p className="hero-description">
            Search satellite imagery using natural language
            and discover meaningful changes across time.
          </p>

          <div className="search-box">

            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe what you want to find..."
            />

            <button onClick={handleSearch}>
              SEARCH →
            </button>

          </div>

          <div className="example-queries">
            <span>TRY:</span>

            <button
              onClick={() => {
                setQuery("Find newly built structures near water");
                setResults(demoScenes);
                setSearched(true);
              }}
            >
              Newly built structures near water
            </button>

            <button
              onClick={() => {
                setQuery("Show road development");
                setResults(demoScenes);
                setSearched(true);
              }}
            >
              Road development
            </button>

            <button
              onClick={() => {
                setQuery("Find water changes");
                setResults(demoScenes);
                setSearched(true);
              }}
            >
              Water changes
            </button>
          </div>

        </section>


        {/* RESULTS */}
        {searched && (
          <section className="results-section">

            <div className="results-header">

              <div>
                <span className="section-label">
                  02 / RETRIEVAL RESULTS
                </span>

                <h3>
                  MATCHED
                  <br />
                  <span>SCENES.</span>
                </h3>
              </div>

              <div className="result-count">
                {results.length} SCENES FOUND
              </div>

            </div>


            <div className="results-grid">

              {results.map((scene, index) => (

                <article
                  className="scene-card"
                  key={scene.id}
                >

                  <div className="scene-top">

                    <span className="scene-rank">
                      #{String(index + 1).padStart(2, "0")}
                    </span>

                    <span className="match-score">
                      {scene.match}% MATCH
                    </span>

                  </div>


                  <div className="scene-image">

                    <div className="image-placeholder">
                      SATELLITE
                      <br />
                      IMAGE
                    </div>

                    <span className="scene-id">
                      {scene.id}
                    </span>

                  </div>


                  <div className="scene-content">

                    <h4>{scene.title}</h4>

                    <p className="scene-description">
                      {scene.description}
                    </p>


                    <div className="scene-meta">

                      <div>
                        <span>LOCATION</span>
                        <strong>{scene.location}</strong>
                      </div>

                      <div>
                        <span>ACQUIRED</span>
                        <strong>{scene.date}</strong>
                      </div>

                      <div>
                        <span>SENSOR</span>
                        <strong>{scene.sensor}</strong>
                      </div>

                      <div>
                        <span>CHANGE</span>
                        <strong>{scene.changeType}</strong>
                      </div>

                    </div>


                    <div className="scene-footer">

                      <div className="tags">

                        {scene.tags.map((tag) => (
                          <span key={tag}>
                            {tag}
                          </span>
                        ))}

                      </div>
                      
                      <button
                        onClick={() => setSelectedScene(scene)}
                      >
                        VIEW DETAILS →
                      </button>

                    </div>

                  </div>

                </article>

              ))}

            </div>

          </section>
        )}
           {selectedScene && (
          <SceneDetail
            scene={selectedScene}
            onBack={() => setSelectedScene(null)}
          />
        )}

      </main>

    </div>
  );
}

export default App;