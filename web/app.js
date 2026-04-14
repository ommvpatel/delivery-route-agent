document.addEventListener("DOMContentLoaded", () => {
  const statusElement = document.getElementById("status");
  const selectedStartElement = document.getElementById("selected-start");
  const selectedStopsElement = document.getElementById("selected-stops");
  const routeSummaryElement = document.getElementById("route-summary");
  const routeOrderElement = document.getElementById("route-order");
  const comparisonSummaryElement = document.getElementById("comparison-summary");
  const comparisonGridElement = document.getElementById("comparison-grid");
  const graphSourceLabelElement = document.getElementById("graph-source-label");
  const graphSourcePathElement = document.getElementById("graph-source-path");
  const costModeElement = document.getElementById("cost-mode");
  const clearSelectionButton = document.getElementById("clear-selection");
  const solveRouteButton = document.getElementById("solve-route");
  const selectionHintElement = document.getElementById("selection-hint");

  if (
    !statusElement ||
    !selectedStartElement ||
    !selectedStopsElement ||
    !routeSummaryElement ||
    !routeOrderElement ||
    !comparisonSummaryElement ||
    !comparisonGridElement ||
    !graphSourceLabelElement ||
    !graphSourcePathElement ||
    !costModeElement ||
    !clearSelectionButton ||
    !solveRouteButton ||
    !selectionHintElement
  ) {
    console.error("One or more required DOM elements were not found.");
    return;
  }

  const map = L.map("map", {
    zoomControl: true,
    attributionControl: true,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const edgeStyle = {
    color: "#6d7c80",
    weight: 4,
    opacity: 0.8,
  };

  const nodeStyle = {
    radius: 7,
    color: "#0b546b",
    fillColor: "#0a7ea4",
    fillOpacity: 0.95,
    weight: 1,
  };

  const startNodeStyle = {
    radius: 9,
    color: "#7a1f1f",
    fillColor: "#d44d3f",
    fillOpacity: 1,
    weight: 2,
  };

  const stopNodeStyle = {
    radius: 8,
    color: "#556b2f",
    fillColor: "#7aa33c",
    fillOpacity: 1,
    weight: 2,
  };

  let selectedStart = null;
  const selectedStops = new Set();
  const nodeMarkers = new Map();
  let solvedRouteLayer = null;

  function updateGraphSource(sourceInfo) {
    if (!sourceInfo) {
      graphSourceLabelElement.textContent = "Unknown";
      graphSourcePathElement.textContent = "No graph source metadata available.";
      return;
    }

    graphSourceLabelElement.textContent = sourceInfo.label ?? sourceInfo.type ?? "Unknown";
    graphSourcePathElement.textContent = sourceInfo.path
      ? `Loaded from ${sourceInfo.path}`
      : "Loaded from an unspecified source.";
  }

  function graphBounds(nodes) {
    return L.latLngBounds(nodes.map((node) => [node.y, node.x]));
  }

  function refreshSidebarSelection() {
    selectedStartElement.textContent = selectedStart ?? "None selected";

    if (selectedStops.size === 0) {
      selectedStopsElement.innerHTML = "<li>No stops selected</li>";
    } else {
      selectedStopsElement.innerHTML = "";
      Array.from(selectedStops)
        .sort()
        .forEach((stop) => {
          const item = document.createElement("li");
          item.textContent = stop;
          selectedStopsElement.appendChild(item);
        });
    }

    const canSolve = selectedStart !== null && selectedStops.size > 0;
    solveRouteButton.disabled = !canSolve;

    if (selectedStart === null) {
      selectionHintElement.textContent =
        "Select a start node and at least one stop to prepare a route request.";
    } else if (selectedStops.size === 0) {
      selectionHintElement.textContent =
        `Start is set to ${selectedStart}. Select one or more stops next.`;
    } else {
      selectionHintElement.textContent =
        `Ready to solve from ${selectedStart} to ${selectedStops.size} stop(s).`;
    }
  }

  function applyMarkerStyle(nodeId) {
    const marker = nodeMarkers.get(nodeId);
    if (!marker) return;

    if (nodeId === selectedStart) {
      marker.setStyle(startNodeStyle);
    } else if (selectedStops.has(nodeId)) {
      marker.setStyle(stopNodeStyle);
    } else {
      marker.setStyle(nodeStyle);
    }
  }

  function refreshAllMarkerStyles() {
    nodeMarkers.forEach((_, nodeId) => {
      applyMarkerStyle(nodeId);
    });
  }

  function handleNodeSelection(nodeId) {
    console.log("Clicked node:", nodeId);

    if (selectedStart === null) {
      selectedStart = nodeId;
    } else if (nodeId === selectedStart) {
      selectedStart = null;
    } else if (selectedStops.has(nodeId)) {
      selectedStops.delete(nodeId);
    } else {
      selectedStops.add(nodeId);
    }

    if (selectedStart !== null && selectedStops.has(selectedStart)) {
      selectedStops.delete(selectedStart);
    }

    refreshSidebarSelection();
    refreshAllMarkerStyles();

    statusElement.textContent =
      `Selected start: ${selectedStart ?? "none"} | Stops: ${Array.from(selectedStops).sort().join(", ") || "none"}`;
  }

  window.handleNodeSelection = handleNodeSelection;

  function clearSelection() {
    selectedStart = null;
    selectedStops.clear();
    refreshSidebarSelection();
    refreshAllMarkerStyles();
    if (solvedRouteLayer) {
      map.removeLayer(solvedRouteLayer);
      solvedRouteLayer = null;
    }
    routeSummaryElement.textContent = "No route solved yet.";
    routeOrderElement.innerHTML = "<li>Delivery order will appear here.</li>";
    comparisonSummaryElement.textContent =
      "Solve a route to compare Greedy, UCS, and A* side by side.";
    comparisonGridElement.innerHTML =
      '<p class="comparison-empty">No comparison results yet.</p>';
    statusElement.textContent = "Selection cleared.";
  }

  function renderComparisonResults(result) {
    const comparisonResults = Array.isArray(result.comparison_results)
      ? result.comparison_results
      : [];
    const bestAlgorithm = result.best_algorithm ?? "Unavailable";

    comparisonSummaryElement.textContent =
      `Best algorithm for this request: ${bestAlgorithm}. Lower cost is better.`;

    comparisonGridElement.innerHTML = "";
    if (comparisonResults.length === 0) {
      comparisonGridElement.innerHTML =
        '<p class="comparison-empty">Comparison results are unavailable for this solve.</p>';
      return;
    }

    comparisonResults.forEach((entry) => {
      const card = document.createElement("div");
      card.className = "comparison-card";
      if (entry.name === bestAlgorithm) {
        card.classList.add("is-best");
      }

      const statesText =
        entry.states_expanded === null ? "n/a" : `${entry.states_expanded}`;
      const costAboveBestText =
        entry.cost_above_best === null ? "n/a" : entry.cost_above_best.toFixed(1);

      card.innerHTML = `
        <p class="comparison-title">${entry.name}</p>
        <p class="comparison-line">Cost: ${entry.total_cost.toFixed(1)} ${result.cost_unit}</p>
        <p class="comparison-line">Above best: ${costAboveBestText}</p>
        <p class="comparison-line">States expanded: ${statesText}</p>
        <p class="comparison-line">Runtime: ${entry.runtime_ms.toFixed(3)} ms</p>
        <p class="comparison-line">Order: ${(entry.delivery_order || []).join(" -> ") || "No route"}</p>
      `;
      comparisonGridElement.appendChild(card);
    });
  }

  function showSolvedRoute(result) {
    if (solvedRouteLayer) {
      map.removeLayer(solvedRouteLayer);
    }

    solvedRouteLayer = L.polyline(result.route_geometry, {
      color: "#d44d3f",
      weight: 6,
      opacity: 0.9,
    }).addTo(map);

    routeSummaryElement.textContent =
      `Solved route cost: ${result.total_cost.toFixed(1)} ${result.cost_unit}. Expanded ${result.states_expanded ?? "n/a"} delivery states using ${result.cost_mode}.`;

    routeOrderElement.innerHTML = "";
    result.delivery_order.forEach((stop) => {
      const item = document.createElement("li");
      item.textContent = stop;
      routeOrderElement.appendChild(item);
    });

    if (result.delivery_order.length === 0) {
      routeOrderElement.innerHTML = "<li>No delivery stops were returned.</li>";
    }

    renderComparisonResults(result);
    updateGraphSource(result.graph_source);
  }

  function drawGraph(graphData) {
    graphData.edges.forEach((edge) => {
      if (!edge.geometry) return;

      L.polyline(edge.geometry, edgeStyle)
        .bindPopup(`${edge.from} ↔ ${edge.to}<br>Weight: ${edge.weight}`)
        .addTo(map);
    });

    graphData.nodes.forEach((node) => {
      if (node.x === undefined || node.y === undefined) return;

      const marker = L.circleMarker([node.y, node.x], nodeStyle)
        .bindPopup(node.id)
        .addTo(map);

      marker.on("click", () => {
        handleNodeSelection(node.id);
      });

      nodeMarkers.set(node.id, marker);
    });

    if (graphData.nodes.length > 0) {
      map.fitBounds(graphBounds(graphData.nodes), { padding: [40, 40] });
    }
  }

  async function loadGraph() {
    try {
      const response = await fetch("/api/graph");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const graphData = await response.json();
      drawGraph(graphData);
      updateGraphSource(graphData.graph_source);
      refreshSidebarSelection();
      statusElement.textContent =
        `Loaded ${graphData.nodes.length} nodes and ${graphData.edges.length} edges from ${graphData.graph_source?.label ?? "the active source"}.`;
    } catch (error) {
      console.error(error);
      statusElement.textContent =
        `Could not load graph data: ${error.message}`;
    }
  }

  clearSelectionButton.addEventListener("click", clearSelection);

  solveRouteButton.addEventListener("click", () => {
    const stops = Array.from(selectedStops).sort();
    const costMode = costModeElement.value;

    fetch("/api/solve-route", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        start: selectedStart,
        stops,
        cost_mode: costMode,
      }),
    })
      .then((response) => response.json().then((payload) => ({ ok: response.ok, payload })))
      .then(({ ok, payload }) => {
        if (!ok) {
          throw new Error(payload.error || "Solve request failed.");
        }

        showSolvedRoute(payload);
        statusElement.textContent =
          `Solved ${payload.cost_mode} route from ${payload.start} through ${payload.delivery_order.join(", ")} using ${payload.graph_source?.label ?? "the active source"}.`;
      })
      .catch((error) => {
        statusElement.textContent = `Could not solve route: ${error.message}`;
      });
  });

  refreshSidebarSelection();
  loadGraph();
});
