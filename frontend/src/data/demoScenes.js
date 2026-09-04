const demoScenes = [
  {
    id: "ORION-001",
    title: "Riverbank Construction Site",
    match: 96,
    location: "24.6139° N, 73.6389° E",
    date: "2026-08-21",
    beforeDate: "2026-05-14",
    sensor: "Sentinel-2",
    resolution: "10 m",
    changeType: "CONSTRUCTION",
    confidence: 94,
    affectedArea: "4.8 ha",
    description:
      "New structures detected along the riverbank with significant surface change compared with the earlier observation.",
    tags: ["NEW STRUCTURES", "RIVERBANK", "HIGH CONFIDENCE"]
  },

  {
    id: "ORION-002",
    title: "Open Ground Vehicle Concentration",
    match: 91,
    location: "25.2048° N, 75.8648° E",
    date: "2026-08-18",
    beforeDate: "2026-06-02",
    sensor: "Sentinel-2",
    resolution: "10 m",
    changeType: "ACTIVITY",
    confidence: 87,
    affectedArea: "7.2 ha",
    description:
      "A previously open area shows a new concentration of high-reflectance objects consistent with vehicle activity.",
    tags: ["ACTIVITY", "OPEN GROUND", "MEDIUM-HIGH CONFIDENCE"]
  },

  {
    id: "ORION-003",
    title: "Expanded Road Network",
    match: 88,
    location: "26.9124° N, 75.7873° E",
    date: "2026-08-11",
    beforeDate: "2026-04-26",
    sensor: "Landsat-9",
    resolution: "15 m",
    changeType: "ROAD DEVELOPMENT",
    confidence: 81,
    affectedArea: "12.6 ha",
    description:
      "New linear features indicate expansion of an existing road network across previously undeveloped terrain.",
    tags: ["ROAD DEVELOPMENT", "LINEAR CHANGE", "MEDIUM CONFIDENCE"]
  },

  {
    id: "ORION-004",
    title: "Water Extent Variation",
    match: 84,
    location: "23.2599° N, 77.4126° E",
    date: "2026-08-05",
    beforeDate: "2026-05-09",
    sensor: "Sentinel-2",
    resolution: "10 m",
    changeType: "WATER VARIATION",
    confidence: 79,
    affectedArea: "21.4 ha",
    description:
      "Water boundaries have shifted significantly between observations, indicating a measurable change in surface water extent.",
    tags: ["WATER", "TEMPORAL CHANGE", "MEDIUM CONFIDENCE"]
  }
];

export default demoScenes;