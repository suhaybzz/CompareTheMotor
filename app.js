const API_BASE = "/api";
const DEFAULT_CAR_A = "fiesta-2019";
const DEFAULT_CAR_B = "corsa-2019";

const carASelect = document.getElementById("carA");
const carBSelect = document.getElementById("carB");
const compareBtn = document.getElementById("compareBtn");
const swapBtn = document.getElementById("swapBtn");
const resetBtn = document.getElementById("resetBtn");
const budgetFilter = document.getElementById("budgetFilter");
const fuelFilter = document.getElementById("fuelFilter");
const buyerType = document.getElementById("buyerType");
const filterSummary = document.getElementById("filterSummary");
const cardA = document.getElementById("cardA");
const cardB = document.getElementById("cardB");
const recommendationBanner = document.getElementById("recommendationBanner");

const registrationInput = document.getElementById("registrationInput");
const lookupBtn = document.getElementById("lookupBtn");
const useLookupForABtn = document.getElementById("useLookupForABtn");
const useLookupForBBtn = document.getElementById("useLookupForBBtn");
const lookupMessage = document.getElementById("lookupMessage");
const lookupResult = document.getElementById("lookupResult");

let filteredVehicles = [];
let lastLookupVehicle = null;
let lastLookupPayload = null;

document.addEventListener("DOMContentLoaded", () => {
  attachEventListeners();
  initialiseApp();
});

function attachEventListeners() {
  compareBtn.addEventListener("click", handleCompare);
  swapBtn.addEventListener("click", handleSwap);
  resetBtn.addEventListener("click", handleReset);
  budgetFilter.addEventListener("change", handleFilterChange);
  fuelFilter.addEventListener("change", handleFilterChange);
  buyerType.addEventListener("change", handleFilterChange);

  lookupBtn.addEventListener("click", handleLookup);
  useLookupForABtn.addEventListener("click", () => assignLookupVehicle("A"));
  useLookupForBBtn.addEventListener("click", () => assignLookupVehicle("B"));

  registrationInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      handleLookup();
    }
  });
}

async function initialiseApp() {
  try {
    await checkBackendHealth();
    await loadVehicles({ useDefaults: true });
  } catch (error) {
    setLookupMessage(
      "Backend not reachable. Start the Flask server first with: python backend/app.py",
      "error"
    );
    console.error(error);
  }
}

async function checkBackendHealth() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error("Backend health check failed.");
  }
}

async function loadVehicles({ keepSelections = true, useDefaults = false } = {}) {
  const previousA = carASelect.value;
  const previousB = carBSelect.value;

  const params = new URLSearchParams({
    max_budget: budgetFilter.value,
    fuel_type: fuelFilter.value,
  });

  const response = await fetch(`${API_BASE}/vehicles?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Could not load vehicles from backend.");
  }

  filteredVehicles = await response.json();
  populateDropdowns(previousA, previousB, keepSelections, useDefaults);
  updateFilterSummary();

  if (useDefaults) {
    await handleCompare();
  }
}

function populateDropdowns(previousA, previousB, keepSelections, useDefaults) {
  const placeholder = `<option value="">Choose a vehicle...</option>`;
  const options =
    placeholder +
    filteredVehicles
      .map(
        (vehicle) =>
          `<option value="${vehicle.id}">${vehicle.make} ${vehicle.model} (${vehicle.year})</option>`
      )
      .join("");

  carASelect.innerHTML = options;
  carBSelect.innerHTML = options;

  if (keepSelections && filteredVehicles.some((vehicle) => vehicle.id === previousA)) {
    carASelect.value = previousA;
  }

  if (keepSelections && filteredVehicles.some((vehicle) => vehicle.id === previousB)) {
    carBSelect.value = previousB;
  }

  if (useDefaults) {
    if (filteredVehicles.some((vehicle) => vehicle.id === DEFAULT_CAR_A)) {
      carASelect.value = DEFAULT_CAR_A;
    }
    if (filteredVehicles.some((vehicle) => vehicle.id === DEFAULT_CAR_B)) {
      carBSelect.value = DEFAULT_CAR_B;
    }
  }
}

async function handleFilterChange() {
  await loadVehicles({ keepSelections: true, useDefaults: false });
  await handleCompare();
}

function updateFilterSummary() {
  const maxBudget = Number(budgetFilter.value);
  const selectedFuel = fuelFilter.value;
  const priority = buyerType.options[buyerType.selectedIndex].text;
  const matchingCars = filteredVehicles.length;

  const budgetText =
    maxBudget >= 999999 ? "No budget limit" : `Maximum budget: £${formatNumber(maxBudget)}`;

  filterSummary.textContent =
    `${budgetText} • Fuel type: ${selectedFuel} • Buyer priority: ${priority} • Matching cars: ${matchingCars}`;
}

async function handleCompare() {
  const vehicleAId = carASelect.value;
  const vehicleBId = carBSelect.value;

  if (!vehicleAId || !vehicleBId) {
    recommendationBanner.classList.add("hidden");
    renderEmptyCard(cardA, "Car A", "Select a vehicle to begin comparison.");
    renderEmptyCard(cardB, "Car B", "Select a second vehicle to compare.");
    cardA.classList.remove("winner", "loser");
    cardB.classList.remove("winner", "loser");
    return;
  }

  if (vehicleAId === vehicleBId) {
    recommendationBanner.classList.remove("hidden");
    recommendationBanner.textContent =
      "Please select two different vehicles so the comparison is meaningful.";
    cardA.classList.remove("winner", "loser");
    cardB.classList.remove("winner", "loser");
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/compare`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        vehicle_a_id: vehicleAId,
        vehicle_b_id: vehicleBId,
        buyer_priority: buyerType.value,
      }),
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Comparison failed.");
    }

    renderVehicleCard(cardA, payload.vehicleA, payload.scoreA, payload.winnerId === payload.vehicleA.id);
    renderVehicleCard(cardB, payload.vehicleB, payload.scoreB, payload.winnerId === payload.vehicleB.id);

    recommendationBanner.classList.remove("hidden");
    recommendationBanner.textContent = payload.recommendation;
    highlightWinner(payload.scoreA.overall, payload.scoreB.overall);
  } catch (error) {
    recommendationBanner.classList.remove("hidden");
    recommendationBanner.textContent = `Comparison error: ${error.message}`;
    recommendationBanner.classList.add("lookup-message", "is-error");
  }
}

async function handleLookup() {
  const registration = registrationInput.value.trim().toUpperCase().replace(/\s+/g, "");

  if (!registration) {
    setLookupMessage("Enter a registration before running the lookup.", "error");
    return;
  }

  useLookupForABtn.disabled = true;
  useLookupForBBtn.disabled = true;
  lastLookupVehicle = null;
  lastLookupPayload = null;

  try {
    const response = await fetch(`${API_BASE}/lookup-registration`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ registration }),
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Lookup failed.");
    }

    lastLookupPayload = payload;
    lastLookupVehicle = payload.vehicle || null;

    if (payload.exactMatch && payload.vehicle) {
      useLookupForABtn.disabled = false;
      useLookupForBBtn.disabled = false;
      setLookupMessage(
        `Lookup successful. ${payload.registration} matched ${payload.vehicle.make} ${payload.vehicle.model} from the ${payload.source} source.`,
        "success"
      );
    } else {
      setLookupMessage(
        `Lookup completed. Official metadata was found for ${payload.registration}, but an exact local comparison record was not matched.`,
        "success"
      );
    }

    renderLookupResult(payload);
  } catch (error) {
    setLookupMessage(`Lookup error: ${error.message}`, "error");
    lookupResult.classList.add("hidden");
  }
}

async function assignLookupVehicle(target) {
  if (!lastLookupVehicle) {
    return;
  }

  const inCurrentFilteredList = filteredVehicles.some(
    (vehicle) => vehicle.id === lastLookupVehicle.id
  );

  if (!inCurrentFilteredList) {
    budgetFilter.value = "999999";
    fuelFilter.value = "All";
    await loadVehicles({ keepSelections: true, useDefaults: false });
    setLookupMessage(
      "The active filters were reset so the looked-up vehicle could be inserted into the comparison.",
      "success"
    );
  }

  if (target === "A") {
    carASelect.value = lastLookupVehicle.id;
  } else {
    carBSelect.value = lastLookupVehicle.id;
  }

  await handleCompare();
}

function setLookupMessage(message, type = "") {
  lookupMessage.textContent = message;
  lookupMessage.classList.remove("is-success", "is-error");

  if (type === "success") {
    lookupMessage.classList.add("is-success");
  }

  if (type === "error") {
    lookupMessage.classList.add("is-error");
  }
}

function renderLookupResult(payload) {
  lookupResult.classList.remove("hidden");

  const exactMatchTags = payload.exactMatch
    ? `<span class="lookup-tag">Exact local match</span>`
    : `<span class="lookup-tag">Partial lookup</span>`;

  const sourceTag = `<span class="lookup-tag">Source: ${payload.source}</span>`;

  if (payload.vehicle) {
    lookupResult.innerHTML = `
      <div class="lookup-result-grid">
        <img src="${payload.vehicle.image}" alt="${payload.vehicle.make} ${payload.vehicle.model}">
        <div>
          <h4>${payload.vehicle.make} ${payload.vehicle.model}</h4>
          <p class="lookup-meta">
            Registration <strong>${payload.registration}</strong> • ${payload.vehicle.year} •
            ${payload.vehicle.engine} • ${payload.vehicle.fuelType}
          </p>
          <p class="lookup-note">
            This result came through the backend lookup flow and can now be sent
            directly into the side-by-side comparison.
          </p>
          <div class="lookup-tags">
            ${exactMatchTags}
            ${sourceTag}
            <span class="lookup-tag">CO₂: ${payload.vehicle.co2} g/km</span>
            <span class="lookup-tag">HP: ${payload.vehicle.horsepower} bhp</span>
          </div>
        </div>
      </div>
    `;
    return;
  }

  const official = payload.officialData || {};
  const suggestions = payload.suggestions || [];

  lookupResult.innerHTML = `
    <div>
      <h4>${official.make || "Unknown make"} • ${official.fuelType || "Unknown fuel type"}</h4>
      <p class="lookup-meta">
        Registration <strong>${payload.registration}</strong> • Year:
        ${official.yearOfManufacture || "N/A"} • CO₂:
        ${official.co2Emissions || "N/A"} g/km
      </p>
      <p class="lookup-note">
        An official registration lookup was completed, but the returned record did
        not map exactly to one local comparison entry.
      </p>
      <div class="lookup-tags">
        ${exactMatchTags}
        ${sourceTag}
      </div>
      ${
        suggestions.length
          ? `<p class="lookup-list"><strong>Nearest available comparison records:</strong> ${suggestions
              .map((item) => `${item.make} ${item.model}`)
              .join(", ")}</p>`
          : ""
      }
    </div>
  `;
}

function renderEmptyCard(container, title, message) {
  container.innerHTML = `
    <div class="empty-state">
      <div>
        <h3>${title}</h3>
        <p>${message}</p>
      </div>
    </div>
  `;
}

function renderVehicleCard(container, vehicle, scores, isWinner) {
  const noteHtml = vehicle.mpgNote
    ? `<div class="note-box"><strong>Note:</strong> ${vehicle.mpgNote}</div>`
    : "";

  container.innerHTML = `
    ${isWinner && scores ? `<div class="winner-badge">🏆 Best Choice</div>` : ""}
    <div class="vehicle-top">
      <img class="vehicle-image" src="${vehicle.image}" alt="${vehicle.make} ${vehicle.model}">
      <h3 class="vehicle-name">${vehicle.make} ${vehicle.model}</h3>
      <p class="vehicle-meta">${vehicle.year} • ${vehicle.engine} • ${vehicle.fuelType}</p>
    </div>

    <section class="metric-section">
      <h4>Vehicle Details</h4>
      <div class="metric-grid">
        ${buildMetricRow("Price", "Lower purchase price is better for affordability.", `£${formatNumber(vehicle.price)}`, 100 - normalise(vehicle.price, 10000, 25000))}
        ${buildMetricRow("Fuel Economy", "Higher MPG generally means lower fuel use.", `${vehicle.mpg} MPG`, normalise(vehicle.mpg, 30, 220))}
        ${buildMetricRow("Insurance Group", "Insurance groups run from 1 to 50. Lower is usually cheaper to insure.", `${vehicle.insuranceGroup}`, 100 - normalise(vehicle.insuranceGroup, 1, 50))}
        ${buildMetricRow("CO₂ Emissions", "Lower CO₂ emissions can mean better environmental performance and lower tax in some cases.", `${vehicle.co2} g/km`, 100 - normalise(vehicle.co2, 0, 180))}
        ${buildMetricRow("Horsepower", "Higher horsepower usually means stronger performance.", `${vehicle.horsepower} bhp`, normalise(vehicle.horsepower, 80, 320))}
      </div>
      ${noteHtml}
    </section>

    <section class="metric-section">
      <h4>Rule-Based Scores</h4>
      <div class="score-grid">
        <div class="score-pill score-affordability">Affordability: ${scores ? scores.affordability : "-"}</div>
        <div class="score-pill score-efficiency">Efficiency: ${scores ? scores.efficiency : "-"}</div>
        <div class="score-pill score-performance">Performance: ${scores ? scores.performance : "-"}</div>
        <div class="score-pill score-overall">Overall: ${scores ? scores.overall : "-"}</div>
      </div>
    </section>

    <div class="summary-box">
      <h5>Summary</h5>
      <p>${generateSummary(vehicle, scores)}</p>
    </div>
  `;
}

function buildMetricRow(label, helpText, value, percentage) {
  const safeValue = Math.max(8, Math.min(100, Math.round(percentage)));
  const fillColor =
    safeValue >= 75
      ? "var(--success)"
      : safeValue >= 50
      ? "var(--warning)"
      : "var(--danger)";

  return `
    <div class="metric-row">
      <div class="metric-label-wrap">
        <span class="metric-label">${label}</span>
        <span class="metric-help" title="${helpText}">i</span>
      </div>
      <span class="metric-value">${value}</span>
      <div class="metric-bar">
        <div class="metric-fill" style="width:${safeValue}%; background:${fillColor};"></div>
      </div>
    </div>
  `;
}

function generateSummary(vehicle, scores) {
  if (!scores) {
    return "Select two different cars to see a meaningful rule-based comparison summary.";
  }

  let strength = "balanced overall";
  if (
    scores.affordability >= scores.efficiency &&
    scores.affordability >= scores.performance
  ) {
    strength = "strongest for affordability-focused buyers";
  } else if (scores.efficiency >= scores.performance) {
    strength = "strongest for buyers prioritising efficiency";
  } else {
    strength = "strongest for buyers prioritising performance";
  }

  return `${vehicle.make} ${vehicle.model} is ${strength}. It offers ${vehicle.mpg} MPG, ${vehicle.horsepower} bhp, an insurance group of ${vehicle.insuranceGroup}, and CO₂ emissions of ${vehicle.co2} g/km.`;
}

function normalise(value, min, max) {
  const clamped = Math.max(min, Math.min(max, value));
  return ((clamped - min) / (max - min)) * 100;
}

function formatNumber(number) {
  return new Intl.NumberFormat("en-GB").format(number);
}

async function handleSwap() {
  const temp = carASelect.value;
  carASelect.value = carBSelect.value;
  carBSelect.value = temp;
  await handleCompare();
}

async function handleReset() {
  budgetFilter.value = "999999";
  fuelFilter.value = "All";
  buyerType.value = "balanced";
  registrationInput.value = "";
  lookupResult.classList.add("hidden");
  useLookupForABtn.disabled = true;
  useLookupForBBtn.disabled = true;
  lastLookupPayload = null;
  lastLookupVehicle = null;
  setLookupMessage(
    "The system has been reset to the default catalogue and weighting profile.",
    "success"
  );
  await loadVehicles({ keepSelections: false, useDefaults: true });
}

function highlightWinner(scoreA, scoreB) {
  cardA.classList.remove("winner", "loser");
  cardB.classList.remove("winner", "loser");

  if (Math.round(scoreA) === Math.round(scoreB)) return;

  if (scoreA > scoreB) {
    cardA.classList.add("winner");
    cardB.classList.add("loser");
  } else {
    cardB.classList.add("winner");
    cardA.classList.add("loser");
  }
}
