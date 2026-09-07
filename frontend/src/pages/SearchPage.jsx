import { useState } from "react";
import { useNavigate } from "react-router-dom";

function SearchPage({
  query,
  setQuery,
  onSearch,
  loading,
  error,
}) {
  const navigate = useNavigate();

  const [localQuery, setLocalQuery] =
    useState(query || "");

  function submitSearch(searchQuery) {
    const trimmedQuery =
      searchQuery.trim();

    if (!trimmedQuery) {
      return;
    }

    setQuery(trimmedQuery);
    onSearch(trimmedQuery);
    navigate("/results");
  }

  function handleSubmit(event) {
    event.preventDefault();
    submitSearch(localQuery);
  }

  function handleExample(example) {
    setLocalQuery(example);
    submitSearch(example);
  }

  return (
    <section className="hero">

      <span className="section-label">
        01 / INTELLIGENCE QUERY
      </span>

      <h2>
        FIND
        <br />
        <span>
          WHAT CHANGED.
        </span>
      </h2>

      <p className="hero-description">
        Search satellite imagery using
        natural language and discover
        meaningful changes across time.
      </p>

      <form
        className="search-box"
        onSubmit={handleSubmit}
      >

        <input
          type="text"
          value={localQuery}
          onChange={(event) =>
            setLocalQuery(
              event.target.value
            )
          }
          placeholder="Describe what you want to find..."
        />

        <button
          type="submit"
          disabled={loading}
        >
          {loading
            ? "SEARCHING..."
            : "SEARCH →"}
        </button>

      </form>

      <div className="example-queries">

        <span>
          TRY:
        </span>

        <button
          type="button"
          onClick={() =>
            handleExample(
              "temporary structures near a river"
            )
          }
        >
          Temporary structures near a river
        </button>

        <button
          type="button"
          onClick={() =>
            handleExample(
              "road development"
            )
          }
        >
          Road development
        </button>

        <button
          type="button"
          onClick={() =>
            handleExample(
              "vegetation and green areas"
            )
          }
        >
          Vegetation and green areas
        </button>

      </div>

      {error && (

        <p
          style={{
            marginTop: "20px",
            color: "#b42318",
            fontWeight: 600,
          }}
        >
          {error}
        </p>

      )}

    </section>
  );
}

export default SearchPage;