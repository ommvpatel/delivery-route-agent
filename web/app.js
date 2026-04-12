document.addEventListener("DOMContentLoaded", () => {
  const statusElement = document.getElementById("status");
  const selectedStartElement = document.getElementById("selected-start");
  const selectedStopsElement = document.getElementById("selected-stops");
  const routeSummaryElement = document.getElementById("route-summary");
  const routeOrderElement = document.getElementById("route-order");
  const costModeElement = document.getElementById("cost-mode");
  const clearSelectionButton = document.getElementById("clear-selection");
  const solveRouteButton = document.getElementById("solve-route");
  const selectionHintElement = document.getElementById("selection-hint");
  const nodeButtonElements = document.querySelectorAll("[data-node-id]");

  if (
    !statusElement ||
    !selectedStartElement ||
    !selectedStopsElement ||
    !routeSummaryElement ||
    !routeOrderElement ||
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
  const nodeButtons = new Map();
  let solvedRouteLayer = null;

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

    nodeButtons.forEach((button, nodeId) => {
      button.classList.remove("is-start", "is-stop");
      if (nodeId === selectedStart) {
        button.classList.add("is-start");
      } else if (selectedStops.has(nodeId)) {
        button.classList.add("is-stop");
      }
    });
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
    statusElement.textContent = "Selection cleared.";
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
      `Solved route cost: ${result.total_cost.toFixed(1)} ${result.cost_unit}. Expanded ${result.states_expanded} delivery states using ${result.cost_mode}.`;

    routeOrderElement.innerHTML = "";
    result.delivery_order.forEach((stop) => {
      const item = document.createElement("li");
      item.textContent = stop;
      routeOrderElement.appendChild(item);
    });

    if (result.delivery_order.length === 0) {
      routeOrderElement.innerHTML = "<li>No delivery stops were returned.</li>";
    }
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

      marker.bindTooltip(node.id, {
        permanent: true,
        direction: "top",
        className: "node-label",
        offset: [0, -8],
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
      refreshSidebarSelection();
      statusElement.textContent =
        `Loaded ${graphData.nodes.length} nodes and ${graphData.edges.length} edges on the real map.`;
    } catch (error) {
      console.error(error);
      statusElement.textContent =
        `Could not load graph data: ${error.message}`;
    }
  }

  nodeButtonElements.forEach((button) => {
    const nodeId = button.dataset.nodeId;
    nodeButtons.set(nodeId, button);

    button.addEventListener("click", () => {
      handleNodeSelection(nodeId);
    });
  });

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
          `Solved ${payload.cost_mode} route from ${payload.start} through ${payload.delivery_order.join(", ")}.`;
      })
      .catch((error) => {
        statusElement.textContent = `Could not solve route: ${error.message}`;
      });
  });

  refreshSidebarSelection();
  loadGraph();
});
